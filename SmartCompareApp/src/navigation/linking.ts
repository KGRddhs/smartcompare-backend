/**
 * W3-15 — the app's ONE linking config, hoisted out of `App()`.
 *
 * It used to be a non-exported `const linking` inside the App component
 * (App.tsx:345-379 at b63a8368), which meant nothing outside the render tree
 * could resolve a URL — including the push-tap handler this unit adds. The
 * body below is the previous config VERBATIM (prefixes, the three
 * client-authored screens, the `redeem?code=` rewrite) plus the three route
 * targets the backend's push deep links need.
 *
 * Registering a path here is the whole fix for "a tap lands nowhere": the
 * backend emits four `qaren://` URLs in push payloads
 * (`app/services/push_service.py:80`, `scripts/cron_expire_bonuses.py:125`,
 * `app/services/reengagement_service.py:326/345/366`) and at base every one of
 * them resolved to `undefined` through the real `getStateFromPath`.
 */
import {
  createNavigationContainerRef,
  getStateFromPath,
  type LinkingOptions,
} from '@react-navigation/native';

import { RootStackParamList } from '../types';

/**
 * The container ref `App.tsx` hands to `<NavigationContainer ref={...}>`.
 * `src/services/pushNavigation.ts` dispatches through it, which is how a tap
 * navigates without rendering anything.
 */
export const navigationRef = createNavigationContainerRef<RootStackParamList>();

export const linking: LinkingOptions<RootStackParamList> = {
  prefixes: ['qaren://', 'https://qaren.app'],
  config: {
    screens: {
      ReferralLanding: 'c/:share_token',
      InviteeQuiz: 'q/:share_token',
      Auth: {
        screens: {
          Register: {
            path: 'r/:code',
            parse: { code: (c: string) => c.toUpperCase() },
          },
        },
      },
      // W3-15 — the backend push targets. Measured decisions:
      //  * `profile/referrals` (push_service.py:80, cron_expire_bonuses.py:125)
      //    goes to the Profile TAB: the ReferralStatusCard the 2026-05-05 plan
      //    named was deleted in Bundle E, and referral status now surfaces as
      //    the bonus-credits tile in MonthStrip (ProfileScreen.tsx:439).
      //  * `cohort/divergence` (reengagement_service.py:345) goes to Home — no
      //    cohort screen exists and the payload carries no id, so this makes
      //    the tap a handled navigation instead of an unhandled link.
      //  * `comparison/:comparison_id` (reengagement_service.py:326/366) is the
      //    same entry History already uses (HistoryScreen.tsx:799,808); a bogus
      //    id renders `results.emptyState.notFound`.
      // NOTE: `RootStackParamList.Main` is `undefined`, not
      // NavigatorScreenParams<MainTabParamList>, so core's PathConfigMap does
      // NOT type-check the two tab keys below — L1/L4 in
      // __tests__/navigation/linking.w315.test.ts are what catch a typo.
      Main: {
        screens: {
          ProfileTab: 'profile/referrals',
          HomeTab: 'cohort/divergence',
        },
      },
      Results: 'comparison/:comparison_id',
    },
  },
  getStateFromPath: (path: string, options: any) => {
    // Rewrite `redeem?code=QR-XXXXXX` → `r/QR-XXXXXX` so the existing
    // pattern handles both URL shapes from social-share copy.
    const redeemMatch = path.match(/^\/?redeem\??(.*)$/);
    if (redeemMatch) {
      const params = new URLSearchParams(redeemMatch[1]);
      const code = params.get('code');
      if (code) {
        return getStateFromPath(`r/${code.toUpperCase()}`, options);
      }
    }
    return getStateFromPath(path, options);
  },
};
