/**
 * Qaren - Main App Entry Point
 * Bottom tabs navigation with splash, auth, and onboarding flows
 */

import React, { useState, useEffect, useCallback } from 'react';
import { I18nManager } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
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
import { features } from './src/config/features';
import LoginScreen from './src/screens/LoginScreen';
import RegisterScreen from './src/screens/RegisterScreen';
import ForgotPasswordScreen from './src/screens/ForgotPasswordScreen';
import HomeScreen from './src/screens/HomeScreen';
import ResultsScreen from './src/screens/ResultsScreen';
import HistoryScreen from './src/screens/HistoryScreen';
import ProfileScreen from './src/screens/ProfileScreen';
import ReferralLandingScreen from './src/screens/ReferralLandingScreen';
import InviteeQuizScreen from './src/screens/InviteeQuizScreen';

// Types
import { RootStackParamList, AuthStackParamList, MainTabParamList } from './src/types';

// Auth
import { verifyAuth, initializeAuth, clearSession, configureGoogleSignIn, type User } from './src/services/authService';
import { tryRegisterPushToken } from './src/services/pushTokenService';

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
          tabBarIcon: ({ color, size }) => <Home size={size} color={color} />,
        }}
      />
      <Tab.Screen
        name="HistoryTab"
        options={{
          tabBarLabel: t('history.title'),
          tabBarIcon: ({ color, size }) => <Clock size={size} color={color} />,
        }}
      >
        {(props) => <HistoryScreen {...props} onLogout={onLogout} />}
      </Tab.Screen>
      <Tab.Screen
        name="ProfileTab"
        options={{
          tabBarLabel: t('profile.title'),
          tabBarIcon: ({ color, size }) => <UserIcon size={size} color={color} />,
        }}
      >
        {(props) => <ProfileScreen {...props} onLogout={onLogout} />}
      </Tab.Screen>
    </Tab.Navigator>
  );
}

export default function App() {
  const fontsLoaded = useAppFonts();
  const [showSplash, setShowSplash] = useState(true);
  const [isLoading, setIsLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [needsPreferences, setNeedsPreferences] = useState(false);
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
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

      // Auth check
      try {
        const authUser = await initializeAuth();
        if (authUser) {
          setUser(authUser);
          setIsAuthenticated(true);
          setNeedsPreferences(!authUser.preferences_completed);
          // F5.4 — fire-and-forget push token registration on every authed
          // launch. Idempotent server-side; silently no-ops on missing
          // module or permission denial.
          tryRegisterPushToken().catch(() => { /* never blocks app boot */ });
        }
      } catch (error) {
        console.error('Auth initialization error:', error);
      }
      setIsLoading(false);
    }
    init();
  }, []);

  const handleSplashFinish = useCallback(() => {
    setShowSplash(false);
  }, []);

  const handleLoginSuccess = useCallback(async () => {
    try {
      const authUser = await verifyAuth();
      if (authUser) {
        setUser(authUser);
        setNeedsPreferences(!authUser.preferences_completed);
        setIsAuthenticated(true);
        // F5.4 — register push token immediately after first signup/login
        // so Loop 2 push lands on the right device for THIS session.
        tryRegisterPushToken().catch(() => { /* swallow */ });
      }
    } catch (error) {
      console.error('Login verification error:', error);
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
  const linking = {
    prefixes: ['qaren://', 'https://qaren.app'],
    config: {
      screens: {
        ReferralLanding: 'c/:share_token',
        InviteeQuiz: 'q/:share_token',
      },
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
            {/* Referral landing is reachable PRE-auth (no signup gate per design 3.5). */}
            <Stack.Screen
              name="ReferralLanding"
              component={ReferralLandingScreen}
            />
            <Stack.Screen name="InviteeQuiz" component={InviteeQuizScreen} />
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
            {/* Authed users tapping a referral link still get the landing page. */}
            <Stack.Screen
              name="ReferralLanding"
              component={ReferralLandingScreen}
            />
            <Stack.Screen name="InviteeQuiz" component={InviteeQuizScreen} />
          </>
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
}
