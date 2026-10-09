U3b follow-ups: the native re-pin of the consent sentence, the LISTING-TRUTH copy, the device check (UB-R15 / UY6 / UB-R13)

## Context
U3b (PR #342 (merged 2026-10-09 20:54, main 6cff57af), session 75) shipped AI consent v2 under decision D3 = C: one disclosure sentence in EN and AR (the AR under the [SPEC] tag, not natively reviewed), the Profile AI-sharing toggle removed, the sheet body scrolling inside a numeric cap. These follow-ups were recorded in the PR body, not built.

## 1. Native re-pin (UB-R15, owner + one small unit)
- The Arabic sentence of `aiConsent.body` (`SmartCompareApp/src/i18n/ar.json`) is listed in `docs/investigations/2026-10-09-session-75-state/NATIVE_REVIEW_S75.md` with the EN twin and the meaning that must survive.
- If the reviewer changes a word: ONE edit moves the fence sha256 of the EN + AR copy (`__tests__/consent/aiConsentV2.s75.test.ts`, today `372c50484085fa859a576a62367c743365735fab6dda31f336552a4ae2a21a02`) and the V4 fence constant together; `AI_CONSENT_VERSION` stays 2 while the meaning is unchanged (a meaning change bumps it to 3 and re-asks every user). Then the OTA that carries U3b (after PR #330 is live, UB-R4).

## 2. LISTING-TRUTH copy (UY6, CT2-m2 / CT2-m4 / n2)
- The Profile eyebrow still reads "Privacy & notifications" (`ProfileScreen.tsx` ~:461-465) while it heads only the notifications master: value -> "Notifications" (EN + AR, native review).
- The Step 5 onboarding headline "Your data, your call." overstates control under D3 = C: reword (EN + AR, native review).
- `docs/privacy-data-inventory.md`: the purposes of rows 3, 4 and 12 and the stale row-12 `api.ts` line anchors.

## 3. Device check (UB-R13 / UY19 / UY20, owner, before the production build)
- Smallest supported iPhone (375x667), EN and AR, Dynamic Type default and AX1-AX5, iPad compatibility mode (`supportsTablet` false), Android `persistentScrollbar`.
- Look at the TOP of the card (icon, title): proxy arithmetic puts about 37 pt of the top padding and icon above the screen edge at AX sizes on a 667-pt screen; the CTAs stay reachable by construction.
- If the iOS scroll-indicator flash is not visible when the sheet opens (the effect fires in the commit before the Modal is presented), move the call to Modal's `onShow` (never a timer).

## 4. Test-side leftovers (cosmetic)
- `__tests__/errorCopy.w314.test.ts:80` passes the deleted key name `profile.aiSharing.errorSave` as an opaque fallback string: rename to a neutral literal.
- `tests/_env_safety.py:116` and `tests/test_backend_cleanup.py:175-182` keep stale comments about the private-key arm (the env NAME list at `_env_safety.py:117` must stay).
- `SmartCompareApp/__mocks__/react-native.ts`: replace the `eslint-disable-next-line react/display-name` on the pre-existing TextInput forwardRef with a `displayName` assignment.
- The U3a server-side consent record (migration + endpoint) is still unfiled as its own unit.

Filed from session 75 (2026-10-09).
