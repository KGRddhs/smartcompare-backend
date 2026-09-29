/**
 * S69 U3 — one-time AI-processing consent (App Review guideline 5.1.2(i)).
 *
 * Before the first byte of a compare leaves the device, the user is told that
 * MYEZ sends what they enter to OpenAI and agrees to it once. Spec:
 * docs/investigations/2026-09-29-session-69-state/U3_AI_CONSENT_SPEC.md R1/R2,
 * R3 as ruled by its spec review:
 *
 *   - Client-only persistence. There is no server slot for this consent
 *     (consent_service.py takes Terms fields only, on account-creating
 *     requests, behind a default-OFF flag), so the record lives in
 *     AsyncStorage under `@qaren_ai_consent_<userId>` as
 *     `{version: AI_CONSENT_VERSION, at: <ISO>}`. The key is per account and
 *     survives logout (logout removes `@qaren_user` + legacy token keys only);
 *     account deletion clears it (EditProfileScreen).
 *   - No user id (no saved user): the sheet still shows and nothing is
 *     dispatched until the user agrees; nothing is persisted, so the grant
 *     lasts only as long as the screen that asked.
 *   - Bumping AI_CONSENT_VERSION re-asks everyone once (a stored record of any
 *     other version does not count).
 *
 * The gate: `ensureAiConsent(ask)` is the single decision point — stored
 * consent of the current version passes at once; otherwise `ask()` shows the
 * sheet and resolves with the user's answer, and an Agree is persisted before
 * it resolves. `useAiConsentGate` binds it to a screen: every dispatch path
 * hands its action to `withAiConsent(action)`, which runs it synchronously
 * once consent is known for this mount and otherwise awaits
 * `ensureAiConsent`. After the sheet was on screen, the action runs only once
 * the sheet has finished dismissing (iOS `onDismiss`), so a follow-up native
 * presentation (photo picker, camera permission alert, a modal route) never
 * clashes with the sheet's own dismissal.
 *
 * The sheet copy must stay true of what the code sends — see the aiConsent.*
 * keys and the evidence in the U3 PR. It must NOT promise an opt-out: the
 * Profile AI-sharing toggle routes nothing today (#266).
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { Platform } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { getSavedUser } from './authService';

/** Bump to re-ask every user once (e.g. when the disclosure changes). */
export const AI_CONSENT_VERSION = 1;

export const AI_CONSENT_KEY_PREFIX = '@qaren_ai_consent_';

export interface AiConsentRecord {
  version: unknown;
  at: string;
}

export function aiConsentStorageKey(userId: string): string {
  return `${AI_CONSENT_KEY_PREFIX}${userId}`;
}

/** The stored record for this account, or null (none, unreadable, no user). */
export async function readAiConsent(userId: string | null): Promise<AiConsentRecord | null> {
  if (!userId) return null;
  try {
    const raw = await AsyncStorage.getItem(aiConsentStorageKey(userId));
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object' || typeof parsed.at !== 'string') return null;
    return { version: parsed.version, at: parsed.at };
  } catch {
    return null;
  }
}

/** True only for a stored record of the CURRENT version for this account. */
export async function hasCurrentAiConsent(userId: string | null): Promise<boolean> {
  const record = await readAiConsent(userId);
  return record !== null && record.version === AI_CONSENT_VERSION;
}

/** Persist an Agree. A null user id persists nothing (ruling R3). */
export async function recordAiConsent(userId: string | null, now: Date = new Date()): Promise<void> {
  if (!userId) return;
  const record: AiConsentRecord = { version: AI_CONSENT_VERSION, at: now.toISOString() };
  try {
    await AsyncStorage.setItem(aiConsentStorageKey(userId), JSON.stringify(record));
  } catch {
    // The user agreed; a storage hiccup only means they are asked again later.
  }
}

/** Remove this account's record (account deletion). */
export async function clearAiConsent(userId: string | null): Promise<void> {
  if (!userId) return;
  try {
    await AsyncStorage.removeItem(aiConsentStorageKey(userId));
  } catch {
    /* nothing to clean up */
  }
}

async function currentUserId(): Promise<string | null> {
  try {
    const user = await getSavedUser();
    return typeof user?.id === 'string' && user.id ? user.id : null;
  } catch {
    return null;
  }
}

/**
 * The gate. Resolves true when a compare may be dispatched: stored consent of
 * the current version for the saved user, or an Agree from `ask()` (persisted
 * before this resolves). Resolves false on "Not now" / the Privacy link.
 */
export async function ensureAiConsent(ask: () => Promise<boolean>): Promise<boolean> {
  const userId = await currentUserId();
  if (await hasCurrentAiConsent(userId)) return true;
  const agreed = await ask();
  if (agreed) await recordAiConsent(userId);
  return agreed;
}

// iOS reports the end of a Modal's dismissal through `onDismiss`; the timer is
// only a safety net there. Android never calls `onDismiss`, so it continues on
// the next tick.
const DISMISS_SAFETY_MS = Platform.OS === 'ios' ? 1000 : 0;

export interface AiConsentSheetProps {
  visible: boolean;
  busy: boolean;
  onAgree: () => void;
  onNotNow: () => void;
  onOpenPrivacy: () => void;
  onDismiss: () => void;
}

export interface AiConsentGate {
  /** Run `action` once AI-processing consent is given; drop it otherwise. */
  withAiConsent: (action: () => void) => void;
  sheetProps: AiConsentSheetProps;
}

/**
 * Screen binding for the gate. `onOpenPrivacy` is called after the sheet has
 * closed (the pending action is dropped), so a modal route such as Legal is
 * never presented behind the sheet.
 */
export function useAiConsentGate(options: { onOpenPrivacy: () => void }): AiConsentGate {
  const [visible, setVisible] = useState(false);
  const [busy, setBusy] = useState(false);

  const grantedRef = useRef(false);
  const gateOpenRef = useRef(false);
  const answerRef = useRef<((agreed: boolean) => void) | null>(null);
  const declineNextRef = useRef<(() => void) | null>(null);
  const afterDismissRef = useRef<(() => void) | null>(null);
  const safetyTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef(true);
  const onOpenPrivacyRef = useRef(options.onOpenPrivacy);
  onOpenPrivacyRef.current = options.onOpenPrivacy;

  const runAfterDismiss = useCallback(() => {
    if (safetyTimerRef.current) {
      clearTimeout(safetyTimerRef.current);
      safetyTimerRef.current = null;
    }
    const next = afterDismissRef.current;
    afterDismissRef.current = null;
    if (next && mountedRef.current) next();
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      if (safetyTimerRef.current) {
        clearTimeout(safetyTimerRef.current);
        safetyTimerRef.current = null;
      }
      afterDismissRef.current = null;
      // Settle an unanswered sheet as "Not now" so nothing dispatches later.
      const answer = answerRef.current;
      answerRef.current = null;
      answer?.(false);
    };
  }, []);

  const closeSheetThen = useCallback(
    (next: (() => void) | null) => {
      afterDismissRef.current = next;
      if (!mountedRef.current) return;
      setBusy(false);
      setVisible(false);
      if (next) {
        if (safetyTimerRef.current) clearTimeout(safetyTimerRef.current);
        safetyTimerRef.current = setTimeout(runAfterDismiss, DISMISS_SAFETY_MS);
      }
    },
    [runAfterDismiss],
  );

  const withAiConsent = useCallback(
    (action: () => void) => {
      if (grantedRef.current) {
        action();
        return;
      }
      // One sheet at a time: a second tap while the gate is open is dropped.
      if (gateOpenRef.current) return;
      gateOpenRef.current = true;
      let shown = false;
      declineNextRef.current = null;

      const ask = () =>
        new Promise<boolean>((resolve) => {
          if (!mountedRef.current) {
            resolve(false);
            return;
          }
          shown = true;
          answerRef.current = resolve;
          setBusy(false);
          setVisible(true);
        });

      void ensureAiConsent(ask)
        .catch(() => false)
        .then((agreed) => {
          gateOpenRef.current = false;
          answerRef.current = null;
          if (agreed) grantedRef.current = true;
          if (!mountedRef.current) return;
          if (!shown) {
            if (agreed) action();
            return;
          }
          const next = agreed ? action : declineNextRef.current;
          declineNextRef.current = null;
          closeSheetThen(next);
        });
    },
    [closeSheetThen],
  );

  const answer = useCallback((agreed: boolean) => {
    const resolve = answerRef.current;
    if (!resolve) return;
    answerRef.current = null;
    if (agreed) setBusy(true);
    resolve(agreed);
  }, []);

  const onAgree = useCallback(() => answer(true), [answer]);
  const onNotNow = useCallback(() => answer(false), [answer]);
  const onOpenPrivacy = useCallback(() => {
    if (!answerRef.current) return;
    declineNextRef.current = () => onOpenPrivacyRef.current();
    answer(false);
  }, [answer]);

  return {
    withAiConsent,
    sheetProps: {
      visible,
      busy,
      onAgree,
      onNotNow,
      onOpenPrivacy,
      onDismiss: runAfterDismiss,
    },
  };
}
