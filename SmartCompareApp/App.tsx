/**
 * SmartCompare - Main App Entry Point
 * With Authentication Flow + Preferences Onboarding
 */

import React, { useState, useEffect } from 'react';
import { StatusBar } from 'expo-status-bar';
import { ActivityIndicator, View } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';

// Import screens
import HomeScreen from './src/screens/HomeScreen';
import CameraScreen from './src/screens/CameraScreen';
import ResultsScreen from './src/screens/ResultsScreen';
import HistoryScreen from './src/screens/HistoryScreen';
import AccountScreen from './src/screens/AccountScreen';
import LoginScreen from './src/screens/LoginScreen';
import RegisterScreen from './src/screens/RegisterScreen';
import ForgotPasswordScreen from './src/screens/ForgotPasswordScreen';
import PreferencesScreen from './src/screens/PreferencesScreen';

// Import auth service
import { verifyAuth, getSavedUser, User, configureGoogleSignIn } from './src/services/authService';

// Configure Google Sign-In at module level (before any component renders)
configureGoogleSignIn();

// Import types
import { RootStackParamList, AuthStackParamList } from './src/types';

const RootStack = createNativeStackNavigator<RootStackParamList>();
const AuthStack = createNativeStackNavigator<AuthStackParamList>();

// Auth Navigator (Login, Register, Forgot Password)
function AuthNavigator({ onLoginSuccess }: { onLoginSuccess: () => void }) {
  return (
    <AuthStack.Navigator
      screenOptions={{
        headerShown: false,
      }}
    >
      <AuthStack.Screen name="Login">
        {(props) => <LoginScreen {...props} onLoginSuccess={onLoginSuccess} />}
      </AuthStack.Screen>
      <AuthStack.Screen name="Register">
        {(props) => <RegisterScreen {...props} onRegisterSuccess={onLoginSuccess} />}
      </AuthStack.Screen>
      <AuthStack.Screen
        name="ForgotPassword"
        component={ForgotPasswordScreen}
      />
    </AuthStack.Navigator>
  );
}

// Main App Navigator (Home, Camera, Results, History)
function MainNavigator({ onLogout }: { onLogout: () => void }) {
  return (
    <RootStack.Navigator
      initialRouteName="Home"
      screenOptions={{
        headerStyle: {
          backgroundColor: '#007AFF',
        },
        headerTintColor: '#FFF',
        headerTitleStyle: {
          fontWeight: 'bold',
        },
      }}
    >
      <RootStack.Screen name="Home" options={{ headerShown: false }}>
        {(props) => <HomeScreen {...props} onLogout={onLogout} />}
      </RootStack.Screen>
      <RootStack.Screen
        name="Camera"
        component={CameraScreen}
        options={{
          title: 'Capture Products',
          headerStyle: {
            backgroundColor: '#000',
          },
        }}
      />
      <RootStack.Screen
        name="Results"
        component={ResultsScreen}
        options={{
          title: 'Results',
          headerBackTitle: 'Back',
        }}
      />
      <RootStack.Screen
        name="History"
        component={HistoryScreen}
        options={{
          title: 'History',
        }}
      />
      <RootStack.Screen
        name="Account"
        component={AccountScreen}
        options={{
          title: 'Account Settings',
        }}
      />
      <RootStack.Screen
        name="Preferences"
        component={PreferencesScreen}
        options={{
          title: 'Preferences',
          headerBackTitle: 'Back',
        }}
      />
    </RootStack.Navigator>
  );
}

export default function App() {
  const [isLoading, setIsLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [needsPreferences, setNeedsPreferences] = useState(false);
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    checkAuthStatus();
  }, []);

  const checkAuthStatus = async () => {
    try {
      const savedUser = await getSavedUser();

      if (savedUser) {
        const verifiedUser = await verifyAuth();

        if (verifiedUser) {
          setUser(verifiedUser);
          setIsAuthenticated(true);
          setNeedsPreferences(!verifiedUser.preferences_completed);
        } else {
          setIsAuthenticated(false);
        }
      } else {
        setIsAuthenticated(false);
      }
    } catch (error) {
      console.error('Auth check error:', error);
      setIsAuthenticated(false);
    } finally {
      setIsLoading(false);
    }
  };

  const handleLoginSuccess = async () => {
    setIsAuthenticated(true);
    const savedUser = await getSavedUser();
    if (savedUser) {
      setUser(savedUser);
      setNeedsPreferences(!savedUser.preferences_completed);
    }
  };

  const handlePreferencesComplete = () => {
    setNeedsPreferences(false);
  };

  const handleLogout = () => {
    setIsAuthenticated(false);
    setNeedsPreferences(false);
    setUser(null);
  };

  if (isLoading) {
    return (
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#F5F5F5' }}>
        <ActivityIndicator size="large" color="#007AFF" />
      </View>
    );
  }

  if (!isAuthenticated) {
    return (
      <NavigationContainer>
        <StatusBar style="auto" />
        <AuthNavigator onLoginSuccess={handleLoginSuccess} />
      </NavigationContainer>
    );
  }

  if (needsPreferences) {
    return (
      <NavigationContainer>
        <StatusBar style="auto" />
        <RootStack.Navigator screenOptions={{ headerShown: false }}>
          <RootStack.Screen name="Preferences" options={{ headerShown: false }}>
            {(props) => (
              <PreferencesScreen
                {...props}
                onComplete={handlePreferencesComplete}
              />
            )}
          </RootStack.Screen>
        </RootStack.Navigator>
      </NavigationContainer>
    );
  }

  return (
    <NavigationContainer>
      <StatusBar style="auto" />
      <MainNavigator onLogout={handleLogout} />
    </NavigationContainer>
  );
}
