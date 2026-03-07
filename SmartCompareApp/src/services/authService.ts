/**
 * Authentication Service - Supabase Auth
 * Handles login, register, logout, and session management
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import { Platform } from 'react-native';
// Native modules loaded lazily — crashes Expo Go if imported at top level
let GoogleSignin: any = null;
let AppleAuthentication: any = null;
let Crypto: any = null;

function getGoogleSignin() {
  if (!GoogleSignin) {
    try {
      GoogleSignin = require('@react-native-google-signin/google-signin').GoogleSignin;
    } catch {
      console.warn('Google Sign-In native module not available (Expo Go?)');
    }
  }
  return GoogleSignin;
}

function getAppleAuth() {
  if (!AppleAuthentication) {
    try {
      AppleAuthentication = require('expo-apple-authentication');
    } catch {
      console.warn('Apple Authentication module not available');
    }
  }
  return AppleAuthentication;
}

function getCrypto() {
  if (!Crypto) {
    try {
      Crypto = require('expo-crypto');
    } catch {
      console.warn('Expo Crypto module not available');
    }
  }
  return Crypto;
}
import api, { API_BASE_URL } from './api';

export interface User {
  id: string;
  email: string;
  created_at?: string;
  preferences_completed?: boolean;
}

export interface AuthResponse {
  success: boolean;
  user?: User;
  token?: string;
  error?: string;
}

const USER_STORAGE_KEY = '@smartcompare_user';
const TOKEN_STORAGE_KEY = '@smartcompare_token';
const REFRESH_TOKEN_KEY = '@smartcompare_refresh_token';

/**
 * Register a new user
 */
export async function register(email: string, password: string): Promise<AuthResponse> {
  try {
    const response = await api.post('/api/v1/auth/register', {
      email,
      password,
    });

    if (response.data.user) {
      await saveUser(response.data.user);
      if (response.data.session?.access_token) {
        await saveToken(response.data.session.access_token);
      }
      if (response.data.session?.refresh_token) {
        await AsyncStorage.setItem(REFRESH_TOKEN_KEY, response.data.session.refresh_token);
      }
      return {
        success: true,
        user: response.data.user,
        token: response.data.session?.access_token,
      };
    }

    return {
      success: false,
      error: response.data.error || 'Registration failed',
    };
  } catch (error: any) {
    console.error('Register error:', error);
    return {
      success: false,
      error: error.response?.data?.detail || error.message || 'Registration failed',
    };
  }
}

/**
 * Login existing user
 */
export async function login(email: string, password: string): Promise<AuthResponse> {
  try {
    const response = await api.post('/api/v1/auth/login', {
      email,
      password,
    });

    if (response.data.user) {
      await saveUser(response.data.user);
      if (response.data.session?.access_token) {
        await saveToken(response.data.session.access_token);
      }
      if (response.data.session?.refresh_token) {
        await AsyncStorage.setItem(REFRESH_TOKEN_KEY, response.data.session.refresh_token);
      }
      return {
        success: true,
        user: response.data.user,
        token: response.data.session?.access_token,
      };
    }

    return {
      success: false,
      error: response.data.error || 'Login failed',
    };
  } catch (error: any) {
    console.error('Login error:', error);
    return {
      success: false,
      error: error.response?.data?.detail || error.message || 'Login failed',
    };
  }
}

/**
 * Logout user
 */
export async function logout(): Promise<void> {
  try {
    const token = await getToken();
    if (token) {
      // Try to logout on server, but don't fail if it doesn't work
      try {
        await api.post('/api/v1/auth/logout', {}, {
          headers: { Authorization: `Bearer ${token}` }
        });
      } catch (e) {
        // Ignore server logout errors
        console.log('Server logout failed, clearing local session');
      }
    }
  } catch (error) {
    console.error('Logout error:', error);
  } finally {
    // Always clear local storage
    await clearSession();
  }
}

/**
 * Refresh session - with graceful error handling
 */
export async function refreshSession(): Promise<AuthResponse> {
  try {
    const refreshToken = await AsyncStorage.getItem(REFRESH_TOKEN_KEY);
    if (!refreshToken) {
      return { success: false, error: 'No refresh token found' };
    }

    const response = await api.post('/api/v1/auth/refresh', {
      refresh_token: refreshToken,
    });

    if (response.data.success && response.data.session?.access_token) {
      // Always save new tokens — this is critical for the 401 interceptor
      await saveToken(response.data.session.access_token);
      if (response.data.session.refresh_token) {
        await AsyncStorage.setItem(REFRESH_TOKEN_KEY, response.data.session.refresh_token);
      }
      // Save user if provided, otherwise keep cached user
      if (response.data.user) {
        await saveUser(response.data.user);
      }
      const user = response.data.user || await getSavedUser();
      return {
        success: true,
        user: user || undefined,
        token: response.data.session.access_token,
      };
    }

    return { success: false, error: 'Refresh failed' };
  } catch (error: any) {
    console.log('Session refresh failed:', error.message);
    
    // If 401, session is invalid - clear it silently
    if (error.response?.status === 401) {
      await clearSession();
      return { success: false, error: 'Session expired' };
    }
    
    // For other errors, don't clear session (might be network issue)
    return {
      success: false,
      error: error.response?.data?.detail || error.message || 'Refresh failed',
    };
  }
}

/**
 * Check if user is logged in (local check)
 */
export async function isLoggedIn(): Promise<boolean> {
  try {
    const user = await getSavedUser();
    const token = await getToken();
    return !!(user && token);
  } catch {
    return false;
  }
}

/**
 * Get current user from storage
 */
export async function getSavedUser(): Promise<User | null> {
  try {
    const userJson = await AsyncStorage.getItem(USER_STORAGE_KEY);
    if (userJson) {
      return JSON.parse(userJson);
    }
  } catch (error) {
    console.error('Error getting saved user:', error);
  }
  return null;
}

/**
 * Save user to storage
 */
async function saveUser(user: User): Promise<void> {
  try {
    await AsyncStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user));
  } catch (error) {
    console.error('Error saving user:', error);
  }
}

/**
 * Get token from storage
 */
export async function getToken(): Promise<string | null> {
  try {
    return await AsyncStorage.getItem(TOKEN_STORAGE_KEY);
  } catch (error) {
    console.error('Error getting token:', error);
    return null;
  }
}

/**
 * Save token to storage
 */
async function saveToken(token: string): Promise<void> {
  try {
    await AsyncStorage.setItem(TOKEN_STORAGE_KEY, token);
  } catch (error) {
    console.error('Error saving token:', error);
  }
}

/**
 * Clear session (logout locally)
 */
export async function clearSession(): Promise<void> {
  try {
    await AsyncStorage.multiRemove([USER_STORAGE_KEY, TOKEN_STORAGE_KEY, REFRESH_TOKEN_KEY]);
  } catch (error) {
    console.error('Error clearing session:', error);
  }
}

/**
 * Initialize auth - check and refresh session on app start
 * Returns user if valid session exists, null otherwise
 */
export async function initializeAuth(): Promise<User | null> {
  try {
    const user = await getSavedUser();
    const token = await getToken();
    
    if (!user || !token) {
      return null;
    }
    
    // Try to refresh, but don't fail if it doesn't work
    const refreshResult = await refreshSession();
    
    if (refreshResult.success && refreshResult.user) {
      return refreshResult.user;
    }
    
    // If refresh failed with 401, session is invalid
    if (refreshResult.error === 'Session expired') {
      return null;
    }
    
    // For other errors (network), return cached user
    return user;
  } catch (error) {
    console.error('Auth initialization error:', error);
    return null;
  }
}

/**
 * Verify auth status and return user if valid
 * Used by App.tsx to check auth state
 */
export async function verifyAuth(): Promise<User | null> {
  return await initializeAuth();
}

// --- Google Sign-In ---

/**
 * Configure Google Sign-In. Call once at app startup.
 * Uses Google Web Client ID from Google Cloud Console.
 */
export function configureGoogleSignIn() {
  const gs = getGoogleSignin();
  if (!gs) return;
  gs.configure({
    webClientId: '21336192767-i9prqks93nrdmb9rg7ho2v1md9bgqgsv.apps.googleusercontent.com',
    offlineAccess: true,
  });
}

/**
 * Sign in with Google. Gets ID token from native SDK, sends to backend.
 */
export async function signInWithGoogle(): Promise<AuthResponse> {
  try {
    const gs = getGoogleSignin();
    if (!gs) return { success: false, error: 'Google Sign-In not available (requires development build)' };
    await gs.hasPlayServices();
    const signInResult = await gs.signIn();
    const idToken = signInResult.data?.idToken;

    if (!idToken) {
      return { success: false, error: 'Failed to get Google ID token' };
    }

    // Send to our backend, which handles Supabase signInWithIdToken
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/social-login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ provider: 'google', id_token: idToken }),
    });

    const data = await response.json();

    if (data.success && data.session?.access_token) {
      await saveToken(data.session.access_token);
      if (data.session.refresh_token) {
        await AsyncStorage.setItem(REFRESH_TOKEN_KEY, data.session.refresh_token);
      }
      if (data.user) await saveUser(data.user);
    }

    return {
      success: data.success,
      user: data.user,
      token: data.session?.access_token,
      error: data.error,
    };
  } catch (error: any) {
    if (error.code === 'SIGN_IN_CANCELLED') {
      return { success: false, error: 'Sign-in cancelled' };
    }
    return { success: false, error: error.message || 'Google sign-in failed' };
  }
}

// --- Apple Sign-In ---
// Note: Apple Sign-In requires Apple Developer subscription to configure.
// The code is built and ready but won't be testable until Apple Developer account is set up.

/**
 * Check if Apple Sign-In is available (iOS 13+)
 */
export async function isAppleSignInAvailable(): Promise<boolean> {
  if (Platform.OS !== 'ios') return false;
  const apple = getAppleAuth();
  if (!apple) return false;
  return await apple.isAvailableAsync();
}

/**
 * Sign in with Apple. Gets identity token from native SDK, sends to backend with nonce.
 */
export async function signInWithApple(): Promise<AuthResponse> {
  try {
    const apple = getAppleAuth();
    const crypto = getCrypto();
    if (!apple || !crypto) return { success: false, error: 'Apple Sign-In not available (requires development build)' };

    // Generate nonce for security
    const rawNonce = Math.random().toString(36).substring(2, 15);
    const hashedNonce = await crypto.digestStringAsync(
      crypto.CryptoDigestAlgorithm.SHA256,
      rawNonce
    );

    const credential = await apple.signInAsync({
      requestedScopes: [
        apple.AppleAuthenticationScope.FULL_NAME,
        apple.AppleAuthenticationScope.EMAIL,
      ],
      nonce: hashedNonce,
    });

    const idToken = credential.identityToken;
    if (!idToken) {
      return { success: false, error: 'Failed to get Apple identity token' };
    }

    // Send to our backend
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/social-login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        provider: 'apple',
        id_token: idToken,
        nonce: rawNonce,
      }),
    });

    const data = await response.json();

    if (data.success && data.session?.access_token) {
      await saveToken(data.session.access_token);
      if (data.session.refresh_token) {
        await AsyncStorage.setItem(REFRESH_TOKEN_KEY, data.session.refresh_token);
      }
      if (data.user) await saveUser(data.user);
    }

    return {
      success: data.success,
      user: data.user,
      token: data.session?.access_token,
      error: data.error,
    };
  } catch (error: any) {
    if (error.code === 'ERR_REQUEST_CANCELED') {
      return { success: false, error: 'Sign-in cancelled' };
    }
    return { success: false, error: error.message || 'Apple sign-in failed' };
  }
}
