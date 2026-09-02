/**
 * Qaren - Main App Entry Point
 * Bottom tabs navigation with splash, auth, and onboarding flows
 */

// Crash reporting MUST init before any other module so we capture
// failures during early imports (font loading, i18n, native bridge).
// See src/services/sentry.ts for the DSN + scrubbing config.
import { initSentry } from './src/services/sentry';
initSentry();

import * as Sentry from '@sentry/react-native';
import React, { useState, useEffect, useCallback } from 'react';
import { I18nManager, StyleSheet } from 'react-native';
import { NavigationContainer, getStateFromPath, type LinkingOptions } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Home, Clock, User as UserIcon } from 'lucide-react-native';
import { useTranslation } from 'react-i18next';
import { StatusBar } from 'expo-status-bar';

// Theme & i18n
import { useAppFonts } from './src/theme/fonts';
import { colors, typography } from './src/theme';
import { getSavedLanguage } from './src/i18n';
import './src/i18n'; // Initialize i18next

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

// Types
import { RootStackParamList, AuthStackParamList, MainTabParamList } from './src/types';

// Auth
import { verifyAuth, initializeAuth, clearSession, configureGoogleSignIn, type User } from './src/services/authService';
// M18 MB-flows-02 — non-UI session-death signal (401 interceptor's
// failed refresh). Subscribed below so a cleared session routes back to
// the Auth stack instead of leaving MainTabs mounted with no token.
import { onSessionInvalid } from './src/services/sessionEvents';
import { tryRegisterPushToken } from './src/services/pushTokenService';
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
      const { default: i18n } = await import('./src/i18n');
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

      // Auth check
      try {
        const authUser = await initializeAuth();
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
      setIsLoading(false);
    }
    init();
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

  // Show splash during font loading, initial auth check, or splash animation
  if (!fontsLoaded || isLoading || showSplash) {
    return <SplashScreen onFinish={handleSplashFinish} />;
  }

  // Deep-link config — qaren.app/c/{token}?ref={code} resolves to
  // ReferralLanding pre-auth (gradual commitment per design 3.5/3.6).
  // qaren.app/r/{code} + qaren://r/{code} resolve to Register with the
  // code pre-filled (Bundle A §1.2). qaren://redeem?code={code} is also
  // supported via the getStateFromPath rewrite below.
  const linking: LinkingOptions<RootStackParamList> = {
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

  return (
    <NavigationContainer linking={linking}>
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
