/**
 * Qaren - Main App Entry Point
 * Bottom tabs navigation with splash, auth, and onboarding flows
 */

// W3-12 — crash reporting is armed by `src/services/sentryBootstrap`, imported
// FIRST in index.ts. It used to be `initSentry()` here, in this module's body,
// which only runs AFTER this file's whole import graph has been evaluated — so
// the certificate-pinning "running unpinned" alarm raised from api.ts's module
// body, and any boot crash in an imported module, reached an uninitialised
// Sentry and was dropped. See src/services/sentry.ts for DSN + scrubbing.

import * as Sentry from '@sentry/react-native';
import React, { useState, useEffect, useCallback } from 'react';
import { I18nManager, StyleSheet } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Home, Clock, User as UserIcon } from 'lucide-react-native';
import { useTranslation } from 'react-i18next';
import { StatusBar } from 'expo-status-bar';

// Theme & i18n
import { useAppFonts } from './src/theme/fonts';
import { colors, typography } from './src/theme';
// B5 — ONE import of the i18n module. Importing it runs i18next's init as a
// side effect, and the default export is the configured instance used by
// init() below. There used to be a second, dynamic import of this same
// module inside init(); it resolved to the already-evaluated module, so it
// bought nothing and only added an await to the boot chain.
import i18n, { getSavedLanguage } from './src/i18n';

// Screens
import SplashScreen from './src/screens/SplashScreen';
import OnboardingScreen from './src/screens/OnboardingScreen';
// Phase 2 redesign — gated by features.ENABLE_NEW_ONBOARDING (Task 24).
// Default OFF; legacy 6-step flow remains the runtime path until canary.
import { NewOnboardingHost } from './src/screens/onboarding/NewOnboardingHost';
import { features, setFlagStableId } from './src/config/features';
// Phase 5 Task 47 — canary bucketing primitive (deterministic per-user
// stable id; powers the ENABLE_NEW_ONBOARDING getter at 10% rollout).
import { getStableId, setStableUserId } from './src/config/featureBucket';
// Phase 3 Task 32 — bottom-nav icon wrapper with active-state polish
// (emerald + dot + scale bounce per design § 4c).
import { TabBarIcon } from './src/components/TabBarIcon';
import LoginScreen from './src/screens/LoginScreen';
import RegisterScreen from './src/screens/RegisterScreen';
import ForgotPasswordScreen from './src/screens/ForgotPasswordScreen';
import HomeScreen from './src/screens/HomeScreen';
import ResultsScreen from './src/screens/ResultsScreen';
// Bundle A — support / preferences / edit-profile screens routed from Profile.
import LegalScreen from './src/screens/LegalScreen';
import ContactUsScreen from './src/screens/ContactUsScreen';
import EditProfileScreen from './src/screens/EditProfileScreen';
import EditPreferencesFlow from './src/screens/EditPreferencesFlow';
import HistoryScreen from './src/screens/HistoryScreen';
import ProfileScreen from './src/screens/ProfileScreen';
import ReferralLandingScreen from './src/screens/ReferralLandingScreen';
import InviteeQuizScreen from './src/screens/InviteeQuizScreen';
import ScanCameraScreen from './src/screens/ScanCameraScreen';
import PaywallScreen from './src/screens/PaywallScreen';
// A9 — force-update gate. The backend has served GET /api/v1/app/version
// since Bundle D with nobody calling it, so APP_FORCE_UPDATE could not
// reach a device. The hook fires that check fire-and-forget (nothing
// awaits it, so boot is untouched) and stays null on every fail-open path;
// the screen below is deliberately outside the navigator — no route in or
// out — and only renders AFTER the splash gate has already released.
import UpdateRequiredScreen from './src/screens/UpdateRequiredScreen';
import { useForcedUpdateGate } from './src/hooks/useForcedUpdateGate';

// Types
import { RootStackParamList, AuthStackParamList, MainTabParamList } from './src/types';

// Auth
import { verifyAuth, initializeAuth, clearSession, configureGoogleSignIn, type User } from './src/services/authService';
// M18 MB-flows-02 — non-UI session-death signal (401 interceptor's
// failed refresh). Subscribed below so a cleared session routes back to
// the Auth stack instead of leaving MainTabs mounted with no token.
import { onSessionInvalid } from './src/services/sessionEvents';
import { tryRegisterPushToken } from './src/services/pushTokenService';
// W3-15 — the deep-link config used to be a non-exported `const` in this
// component, so nothing outside the render tree could resolve a URL. It now
// lives in one place and is shared by the container and the push-tap handler.
import { linking, navigationRef } from './src/navigation/linking';
import { installPushTapListeners, onNavigationReady } from './src/services/pushNavigation';
// Bundle B/C/D Task 2.11 — Play Install Referrer hand-off into the
// module-scoped invite-code slot consumed later by RegisterScreen.
import { tryReadPlayInstallReferrer } from './src/services/playInstallReferrerService';
import { setDeferredInviteCode } from './src/services/deferredInviteCode';

// Configure Google Sign-In at module level
configureGoogleSignIn();

const Stack = createNativeStackNavigator<RootStackParamList>();
const Tab = createBottomTabNavigator<MainTabParamList>();
const AuthStack = createNativeStackNavigator<AuthStackParamList>();

// Auth Navigator - Login, Register, ForgotPassword
function AuthNavigator({ onLoginSuccess }: { onLoginSuccess: () => void }) {
  return (
    <AuthStack.Navigator screenOptions={{ headerShown: false }}>
      <AuthStack.Screen name="Login">
        {(props) => <LoginScreen {...props} onLoginSuccess={onLoginSuccess} />}
      </AuthStack.Screen>
      <AuthStack.Screen name="Register">
        {(props) => <RegisterScreen {...props} onRegisterSuccess={onLoginSuccess} />}
      </AuthStack.Screen>
      <AuthStack.Screen name="ForgotPassword" component={ForgotPasswordScreen} />
    </AuthStack.Navigator>
  );
}

// Main Tabs Navigator - Home, History, Profile
function MainTabs({ onLogout }: { onLogout: () => void }) {
  const { t } = useTranslation();
  return (
    <Tab.Navigator
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: colors.accent,
        tabBarInactiveTintColor: colors.text.placeholder,
        tabBarStyle: {
          // Phase 3 § 4c — white bg + 1px top border, RTL auto-mirrors.
          borderTopWidth: StyleSheet.hairlineWidth,
          borderTopColor: colors.border.light,
          backgroundColor: colors.bg.primary,
        },
        tabBarLabelStyle: { ...typography.small, fontWeight: '500' },
      }}
    >
      <Tab.Screen
        name="HomeTab"
        component={HomeScreen}
        options={{
          tabBarLabel: t('app.name'),
          tabBarIcon: ({ size, focused }) => (
            <TabBarIcon focused={focused} size={size} Icon={Home} testID="tab-home" />
          ),
        }}
      />
      <Tab.Screen
        name="HistoryTab"
        options={{
          tabBarLabel: t('history.title'),
          tabBarIcon: ({ size, focused }) => (
            <TabBarIcon focused={focused} size={size} Icon={Clock} testID="tab-history" />
          ),
        }}
      >
        {(props) => <HistoryScreen {...props} onLogout={onLogout} />}
      </Tab.Screen>
      <Tab.Screen
        name="ProfileTab"
        options={{
          tabBarLabel: t('profile.title'),
          tabBarIcon: ({ size, focused }) => (
            <TabBarIcon focused={focused} size={size} Icon={UserIcon} testID="tab-profile" />
          ),
        }}
      >
        {(props) => <ProfileScreen {...props} onLogout={onLogout} />}
      </Tab.Screen>
    </Tab.Navigator>
  );
}

function App() {
  const fontsLoaded = useAppFonts();
  const [showSplash, setShowSplash] = useState(true);
  const [isLoading, setIsLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [needsPreferences, setNeedsPreferences] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  // A9 — null until (and unless) the backend affirmatively reports this
  // install below APP_MIN_VERSION with APP_FORCE_UPDATE on.
  const forcedUpdate = useForcedUpdateGate();

  useEffect(() => {
    // Bundle B/C/D Task 2.11 — Android Play Install Referrer hand-off.
    // Fire-and-forget on the same tick as boot so the QR code lands in
    // the module-scoped slot before the user can navigate to Register.
    // No-op on iOS / non-Play-Store installs / missing native module.
    tryReadPlayInstallReferrer()
      .then((code) => {
        if (code) setDeferredInviteCode(code);
      })
      .catch(() => { /* never blocks app boot */ });

    async function init() {
      // Set language + RTL before rendering
      const lang = await getSavedLanguage();
      await i18n.changeLanguage(lang);
      const shouldBeRTL = lang === 'ar';
      if (I18nManager.isRTL !== shouldBeRTL) {
        I18nManager.allowRTL(true);
        I18nManager.forceRTL(shouldBeRTL);
      }

      // Phase 5 Task 47 — resolve stable id for the canary bucket BEFORE
      // any code reads features.ENABLE_NEW_ONBOARDING. Uses persistent
      // device-id pre-signup; switches to user.id below once auth lands.
      // Doing this before setNeedsPreferences keeps the onboarding-gating
      // render in step with the bucket's final value (no flicker).
      const initialId = await getStableId();
      setFlagStableId(initialId);

      // Auth check.
      // A3 — initializeAuth resolves from the CACHED user and refreshes in
      // the background, so this await no longer holds the splash for a
      // network round trip. The callback below re-syncs once that
      // background refresh lands; a dead session takes the
      // onSessionInvalid path wired in the effect further down.
      try {
        const authUser = await initializeAuth((refreshedUser) => {
          setUser(refreshedUser);
          // Only ever LOWER the onboarding gate. A user who finished
          // onboarding on another device stops seeing it; a user who is
          // mid-onboarding on THIS device can never be thrown back into
          // it by a late server read.
          if (refreshedUser.preferences_completed) {
            setNeedsPreferences(false);
          }
        });
        if (authUser) {
          // Re-bucket on the user.id post-login so the canary follows
          // the user across devices (same user.id → same bucket).
          setStableUserId(authUser.id);
          setFlagStableId(authUser.id);

          setUser(authUser);
          setIsAuthenticated(true);
          setNeedsPreferences(!authUser.preferences_completed);
          // F5.4 — fire-and-forget push token registration on every authed
          // launch. Idempotent server-side; silently no-ops on missing
          // module or permission denial.
          tryRegisterPushToken().catch(() => { /* never blocks app boot */ });
        }
      } catch (error) {
        if (__DEV__) console.error('Auth initialization error:', error);
      }
    }

    // B5 — the splash gate is released on EVERY path.
    //
    // `setIsLoading(false)` used to be the last statement INSIDE init(),
    // after four awaits (saved language, i18n.changeLanguage, stable id,
    // auth) of which only the auth one was wrapped in a try/catch. A
    // rejection anywhere earlier skipped it, and because the render below
    // returns <SplashScreen> while `isLoading` is true — with no retry, no
    // timeout and no error surface — the app would have sat on the splash
    // for the rest of the process. Every awaited callee happens to guard
    // itself today, so this closes a latent stranding path rather than a
    // reproduced hang.
    //
    // On that failure path the language/RTL side effects above have not
    // applied, so the app renders at i18next's configured default ('en')
    // instead of the saved language. That is strictly better than a frozen
    // splash: the user reaches Main/Auth and can switch language from
    // Profile.
    init()
      .catch((error) => {
        if (__DEV__) console.error('App initialization error:', error);
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, []);

  // M18 MB-flows-02 — `setIsAuthenticated(false)` previously lived ONLY
  // in the user-initiated handleLogout, so a session cleared by
  // api.performRefresh (dead refresh token mid-session) left the app
  // rendering MainTabs with no token and no route back to Auth. The
  // emitter sites have already cleared the session, so this listener
  // only downgrades state — calling clearSession here again would risk
  // an emit->logout->emit loop if the emitters ever move.
  useEffect(() => {
    const unsubscribe = onSessionInvalid(() => {
      setIsAuthenticated(false);
      setNeedsPreferences(false);
      setUser(null);
    });
    return unsubscribe;
  }, []);

  // W3-15 — arm the notification-response listener and the foreground
  // presentation handler at boot. Deliberately its OWN effect and NOT part of
  // the awaited init() block: a tap that launched the app arrives while the
  // splash is still up, so the listener has to exist before auth resolves —
  // it parks the tap and onNavigationReady below drains it. The returned
  // unsubscribe is the effect's cleanup.
  useEffect(() => installPushTapListeners(), []);

  const handleSplashFinish = useCallback(() => {
    setShowSplash(false);
  }, []);

  const handleLoginSuccess = useCallback(async () => {
    try {
      const authUser = await verifyAuth();
      if (authUser) {
        // Phase 5 Task 47 — re-bucket on user.id at fresh login so the
        // canary follows the user across devices.
        setStableUserId(authUser.id);
        setFlagStableId(authUser.id);

        setUser(authUser);
        setNeedsPreferences(!authUser.preferences_completed);
        setIsAuthenticated(true);
        // F5.4 — register push token immediately after first signup/login
        // so Loop 2 push lands on the right device for THIS session.
        tryRegisterPushToken().catch(() => { /* swallow */ });
      } else if (__DEV__) {
        // M18 MB-flows-03 (secondary) — the auth screen reported success
        // but no usable session exists locally. The primary trigger
        // (registration pending email confirmation) is now intercepted in
        // RegisterScreen before this callback fires; reaching here means
        // a login/social path stored no token, so we stay on the Auth
        // stack (isAuthenticated remains false) and make the no-op
        // visible instead of silently swallowing it.
        console.warn('[AUTH] Login callback fired but no valid local session was found');
      }
    } catch (error) {
      if (__DEV__) console.error('Login verification error:', error);
    }
  }, []);

  const handleLogout = useCallback(async () => {
    await clearSession();
    setIsAuthenticated(false);
    setNeedsPreferences(false);
    setUser(null);
  }, []);

  const handlePreferencesComplete = useCallback(() => {
    setNeedsPreferences(false);
  }, []);

  // Show splash during font loading, initial auth check, or splash animation.
  // A5 — `ready` lets the splash end its brand-moment floor early once there
  // is nothing left to wait for, instead of charging a flat 1.5s on top of
  // native startup. It still caps at 1.5s, so a slow boot is unchanged.
  if (!fontsLoaded || isLoading || showSplash) {
    return (
      <SplashScreen onFinish={handleSplashFinish} ready={fontsLoaded && !isLoading} />
    );
  }

  // A9 — force-update gate, deliberately placed AFTER the splash return and
  // BEFORE the navigator. After, because the check is fire-and-forget and
  // must never hold boot: an app that has not finished booting cannot be
  // used anyway, so there is nothing to gain by racing it. Before, because
  // the block has to replace the navigator outright — rendering it as a
  // route would leave a dismissable modal over a usable app.
  if (forcedUpdate) {
    return <UpdateRequiredScreen updateUrl={forcedUpdate.updateUrl} />;
  }

  return (
    <NavigationContainer ref={navigationRef} linking={linking} onReady={onNavigationReady}>
      <StatusBar style="auto" />
      <Stack.Navigator screenOptions={{ headerShown: false }}>
        {!isAuthenticated ? (
          <>
            <Stack.Screen name="Auth">
              {(props) => <AuthNavigator {...props} onLoginSuccess={handleLoginSuccess} />}
            </Stack.Screen>
          </>
        ) : needsPreferences ? (
          <Stack.Screen name="Onboarding">
            {(props) =>
              features.ENABLE_NEW_ONBOARDING ? (
                // Phase 2 17-step flow. Same onComplete contract so this is
                // a drop-in replacement; the Phase 5 canary plan flips the
                // flag in stages 10% → 50% → 100%.
                <NewOnboardingHost onComplete={() => handlePreferencesComplete()} />
              ) : (
                <OnboardingScreen {...props} onComplete={handlePreferencesComplete} />
              )
            }
          </Stack.Screen>
        ) : (
          <>
            <Stack.Screen name="Main">
              {(props) => <MainTabs {...props} onLogout={handleLogout} />}
            </Stack.Screen>
            <Stack.Screen
              name="Results"
              component={ResultsScreen}
              options={{ presentation: 'modal' }}
            />
            {/* Bundle A — Privacy + Terms (shared screen, switched by route param). */}
            <Stack.Screen
              name="Legal"
              component={LegalScreen}
              options={{ presentation: 'modal' }}
            />
            <Stack.Screen
              name="ContactUs"
              component={ContactUsScreen}
              options={{ presentation: 'modal' }}
            />
            <Stack.Screen
              name="EditProfile"
              options={{ presentation: 'modal' }}
            >
              {(props) => (
                <EditProfileScreen {...props} onAccountDeleted={handleLogout} />
              )}
            </Stack.Screen>
            <Stack.Screen
              name="EditPreferences"
              component={EditPreferencesFlow}
              options={{ presentation: 'modal' }}
            />
            {/* Bundle E F-S1.5j (2026-05-28): renamed from "Onboarding" to
                "OnboardingEdit" to resolve the RN-Navigation v7 duplicate-
                route-name pattern. The fresh-flow Stack.Screen at L302 also
                used name="Onboarding"; React Navigation treated the two as
                the same route, so when `needsPreferences` flipped false
                after Step 17 fired onComplete, the navigator refused to
                swap routes and the user stayed stuck on Step 17. Mirrors
                the main-lane hotfix at 2e1ceb7 + memory feedback file
                `feedback_react_navigation_duplicate_route_name.md`.
                F-S1.5c/d consolidation already repointed every
                "edit style profile" caller to EditPreferences, so this
                modal entry has zero direct navigators today; the route
                stays registered with a distinct name so future bundles
                can reuse it without re-triggering the collision. */}
            <Stack.Screen
              name="OnboardingEdit"
              options={{ presentation: 'modal', headerShown: false }}
            >
              {(props) =>
                features.ENABLE_NEW_ONBOARDING ? (
                  <NewOnboardingHost
                    mode={props.route.params?.mode ?? 'full'}
                    onComplete={() => props.navigation.goBack()}
                    onEditDone={() => props.navigation.goBack()}
                  />
                ) : (
                  <OnboardingScreen
                    {...props}
                    onComplete={() => props.navigation.goBack()}
                  />
                )
              }
            </Stack.Screen>
            {/* Bundle B/C/D — Cal-AI-style fullscreen camera. See plan § Task 1.8. */}
            <Stack.Screen
              name="ScanCamera"
              component={ScanCameraScreen}
              options={{ presentation: 'modal', headerShown: false }}
            />
            {/* Freemium gate — bottom-sheet overlay reachable from HomeScreen
                (text/url/scan compare on canCompare=false, PaywallBanner CTA,
                chip taps) and ResultsScreen vision USAGE_LIMIT path. */}
            <Stack.Screen
              name="Paywall"
              component={PaywallScreen}
              options={{
                presentation: 'transparentModal',
                animation: 'slide_from_bottom',
                headerShown: false,
              }}
            />
          </>
        )}

        {/* Bundle E F-S1.5m (2026-05-29): hoisted out of both auth branches.
            ReferralLanding + InviteeQuiz were previously hand-copied into
            pre-auth and post-auth branches under the same `name` props,
            which collapsed in React Navigation v7 as the same logical
            route (same shape as F-S1.5j Onboarding fix). Both screens
            handle their own auth-state branching internally, so they
            don't need to live inside the conditional. Registering them
            once at the Navigator-level keeps the linking config (L258:
            `c/:share_token` → ReferralLanding, `q/:share_token` →
            InviteeQuiz) unchanged and avoids the duplicate-name pattern
            from memory feedback_react_navigation_duplicate_route_name.md. */}
        <Stack.Screen
          name="ReferralLanding"
          component={ReferralLandingScreen}
        />
        <Stack.Screen name="InviteeQuiz" component={InviteeQuizScreen} />
      </Stack.Navigator>
    </NavigationContainer>
  );
}

// Sentry.wrap installs error boundaries + touch/navigation tracing on
// the root component. Falls back to a passthrough if the SDK ever drops
// the export in a future version.
export default (typeof Sentry.wrap === 'function' ? Sentry.wrap(App) : App);
