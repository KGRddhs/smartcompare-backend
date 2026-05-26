/**
 * Authentication Service - Supabase Auth
 * Handles login, register, logout, and session management
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';
import * as Sentry from '@sentry/react-native';
// Native modules loaded lazily — crashes Expo Go if imported at top level
let GoogleSignin: any = null;
let AppleAuthentication: any = null;
let Crypto: any = null;

function getGoogleSignin() {
  if (!GoogleSignin) {
    try {
      GoogleSignin = require('@react-native-google-signin/google-signin').GoogleSignin;
    } catch {
      if (__DEV__) console.warn('Google Sign-In native module not available (Expo Go?)');
    }
  }
  return GoogleSignin;
}

function getAppleAuth() {
  if (!AppleAuthentication) {
    try {
      AppleAuthentication = require('expo-apple-authentication');
    } catch {
      if (__DEV__) console.warn('Apple Authentication module not available');
    }
  }
  return AppleAuthentication;
}

function getCrypto() {
  if (!Crypto) {
    try {
      Crypto = require('expo-crypto');
    } catch {
      if (__DEV__) console.warn('Expo Crypto module not available');
    }
  }
  return Crypto;
}
import api, { API_BASE_URL } from './api';
import { getDeviceFingerprint } from './deviceFingerprint';

export interface User {
  id: string;
  email: string;
  display_name?: string;
  auth_provider?: string;
  created_at?: string;
  preferences_completed?: boolean;
}

export interface AuthResponse {
  success: boolean;
  user?: User;
  token?: string;
  error?: string;
}

const USER_STORAGE_KEY = '@qaren_user'; // AsyncStorage — '@' prefix valid
const TOKEN_STORAGE_KEY = 'qaren_token'; // SecureStore — '@' prefix INVALID, would error
const REFRESH_TOKEN_KEY = 'qaren_refresh_token'; // SecureStore — '@' prefix INVALID

export interface RegisterOptions {
  name?: string;
  inviteId?: string;
  inviteCode?: string;
}

/**
 * Register a new user.
 *
 * Accepts EITHER a string `inviteId` (legacy positional) OR a
 * `RegisterOptions` object. Always sends X-Device-Fingerprint header so
 * the backend can lock free-tier counters to the physical device across
 * re-signups. See Bundle A design §1.5 + §1.1.
 */
export async function register(
  email: string,
  password: string,
  inviteOrOptions?: string | RegisterOptions
): Promise<AuthResponse> {
  const options: RegisterOptions =
    typeof inviteOrOptions === 'string'
      ? { inviteId: inviteOrOptions }
      : inviteOrOptions ?? {};

  let fingerprint: string | null = null;
  try {
    fingerprint = await getDeviceFingerprint();
  } catch (e) {
    if (__DEV__) console.warn('[AUTH] device fingerprint unavailable:', e);
  }

  try {
    const response = await api.post(
      '/api/v1/auth/register',
      {
        email,
        password,
        ...(options.name ? { name: options.name } : {}),
        ...(options.inviteId ? { invite_id: options.inviteId } : {}),
        ...(options.inviteCode ? { invite_code: options.inviteCode } : {}),
      },
      fingerprint ? { headers: { 'X-Device-Fingerprint': fingerprint } } : undefined,
    );

    if (response.data.user) {
      await saveUser(response.data.user);
      if (__DEV__) console.log('[AUTH] Register - access_token present:', !!response.data.session?.access_token);
      if (response.data.session?.access_token) {
        await saveToken(response.data.session.access_token);
      } else {
        if (__DEV__) console.warn('[AUTH] No access_token after register — email confirmation may be required');
      }
      if (response.data.session?.refresh_token) {
        await SecureStore.setItemAsync(REFRESH_TOKEN_KEY, response.data.session.refresh_token);
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
    if (__DEV__) console.error('Register error:', error);
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
      if (__DEV__) console.log('[AUTH] Login - access_token present:', !!response.data.session?.access_token);
      if (response.data.session?.access_token) {
        await saveToken(response.data.session.access_token);
      } else {
        if (__DEV__) console.warn('[AUTH] No access_token after login');
      }
      if (response.data.session?.refresh_token) {
        await SecureStore.setItemAsync(REFRESH_TOKEN_KEY, response.data.session.refresh_token);
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
    if (__DEV__) console.error('Login error:', error);
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
        if (__DEV__) console.log('Server logout failed, clearing local session');
      }
    }
  } catch (error) {
    if (__DEV__) console.error('Logout error:', error);
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
    const refreshToken = await SecureStore.getItemAsync(REFRESH_TOKEN_KEY);
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
        await SecureStore.setItemAsync(REFRESH_TOKEN_KEY, response.data.session.refresh_token);
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
    if (__DEV__) console.log('Session refresh failed:', error.message);
    
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
    if (__DEV__) console.error('Error getting saved user:', error);
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
    if (__DEV__) console.error('Error saving user:', error);
  }
}

/**
 * Get token from storage
 */
export async function getToken(): Promise<string | null> {
  try {
    return await SecureStore.getItemAsync(TOKEN_STORAGE_KEY);
  } catch (error) {
    if (__DEV__) console.error('Error getting token:', error);
    return null;
  }
}

/**
 * Save token to storage
 */
async function saveToken(token: string): Promise<void> {
  try {
    await SecureStore.setItemAsync(TOKEN_STORAGE_KEY, token);
  } catch (error) {
    if (__DEV__) console.error('Error saving token:', error);
  }
}

/**
 * Clear session (logout locally)
 */
export async function clearSession(): Promise<void> {
  try {
    await SecureStore.deleteItemAsync(TOKEN_STORAGE_KEY);
    await SecureStore.deleteItemAsync(REFRESH_TOKEN_KEY);
    await AsyncStorage.removeItem(USER_STORAGE_KEY); // User profile is non-secret
  } catch (error) {
    if (__DEV__) console.error('Error clearing session:', error);
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
    if (__DEV__) console.error('Auth initialization error:', error);
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

/**
 * Request password reset email via Supabase
 */
export async function requestPasswordReset(email: string): Promise<void> {
  try {
    const response = await api.post('/api/v1/auth/password-reset', { email });
    if (!response.data.success) {
      throw new Error(response.data.error || 'Password reset request failed');
    }
  } catch (error: any) {
    if (error.response?.data?.detail) {
      throw new Error(error.response.data.detail);
    }
    throw error;
  }
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
    // iOS client ID is REQUIRED when GoogleService-Info.plist is absent from
    // the EAS preview build (post-merge device-leg, 2026-05-25). Derived from
    // `expo.ios.googleServicesFile`-equivalent iosUrlScheme in app.json by
    // reversing the dot order:
    //   iosUrlScheme:  com.googleusercontent.apps.<suffix>
    //   iosClientId:   <suffix>.apps.googleusercontent.com
    // Without this, @react-native-google-signin throws "failed to determine
    // clientID" on the first Google button tap (Sentry REACT-NATIVE-2).
    iosClientId: '21336192767-38hi4t1ac23089iau7jdog1f43oc7rdm.apps.googleusercontent.com',
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

    // Bundle E B4 fix (2026-05-26, Ahmed device repro on EAS preview):
    // Google's iOS native SDK auto-generates a `nonce` and embeds it as a claim
    // in the issued idToken. Path A R1 (Bundle D Phase 3) stopped FE from
    // sending the nonce on the assumption Google's SDK doesn't bind one — that
    // was wrong. Supabase verifies parity: "Passed nonce and nonce in id_token
    // should either both exist or not." Since the idToken has a nonce claim,
    // we must read it from the token payload + echo it back so Supabase's
    // hash(raw_nonce) === idToken.nonce check holds.
    //
    // Real replay protection still comes from: Supabase audience check (aud =
    // iosClientId), Google's RS256 signature, and the short token TTL.
    //
    // Diagnostic Sentry captures remain in place until a clean B4 ships green
    // — they auto-no-op when sign-in succeeds.
    const signInResult = await gs.signIn();
    const idToken = signInResult.data?.idToken;
    const sdkResultKeys = Object.keys(signInResult?.data || {}).join(',') || '(empty)';

    if (!idToken) {
      const msg = `[B4-DIAG] no idToken from native SDK. signInResult.data keys: [${sdkResultKeys}].`;
      Sentry.captureMessage(msg, { level: 'error', tags: { b4_diag: 'no_idtoken' }, extra: { sdkResultKeys, signInResultShape: Object.keys(signInResult || {}).join(',') } });
      return {
        success: false,
        error: `${msg} Likely: Supabase iOS Client ID mismatch in app.json plugin config OR Google Cloud OAuth iOS bundle ID (com.qaren.app) not registered. Send this whole message to dispatcher.`,
      };
    }

    const parts = idToken.split('.');
    const diagHead = `len=${idToken.length} parts=${parts.length} head=${idToken.substring(0, 24)}`;
    console.log('[GOOGLE-DIAG]', diagHead);
    Sentry.addBreadcrumb({ category: 'b4_diag', level: 'info', message: '[GOOGLE-DIAG] ' + diagHead });

    // Decode the idToken payload to extract the nonce claim Google embedded.
    // base64url-decode payload (middle segment), parse JSON, read .nonce.
    // Safe failure mode: if decode fails or no nonce present, send without —
    // the backend's `if nonce:` guard will skip the Supabase nonce param.
    let tokenNonce: string | undefined;
    try {
      const payloadB64 = parts[1].replace(/-/g, '+').replace(/_/g, '/');
      const padded = payloadB64 + '='.repeat((4 - (payloadB64.length % 4)) % 4);
      // atob is available in Hermes/iOS RN; falls back to global if not.
      const decoded = typeof atob === 'function' ? atob(padded) : '';
      if (decoded) {
        const claims = JSON.parse(decoded);
        if (typeof claims.nonce === 'string' && claims.nonce.length > 0) {
          tokenNonce = claims.nonce;
        }
      }
    } catch (decodeErr: any) {
      Sentry.addBreadcrumb({ category: 'b4_diag', level: 'warning', message: 'nonce decode failed: ' + (decodeErr?.message || 'unknown') });
    }

    const body: Record<string, string> = { provider: 'google', id_token: idToken };
    if (tokenNonce) {
      body.nonce = tokenNonce;
      Sentry.addBreadcrumb({ category: 'b4_diag', level: 'info', message: `nonce echoed from id_token claim (len=${tokenNonce.length})` });
    }

    let response: Response;
    try {
      response = await fetch(`${API_BASE_URL}/api/v1/auth/social-login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
    } catch (netErr: any) {
      const msg = `[B4-DIAG] network/cert-pin failure before backend. ${diagHead} err=${netErr?.message || 'unknown'}`;
      Sentry.captureMessage(msg, { level: 'error', tags: { b4_diag: 'network' }, extra: { errMessage: netErr?.message, errCode: netErr?.code } });
      return {
        success: false,
        error: `${msg}. Likely: certificatePinning.ts SPKI pin stale OR API_BASE_URL unreachable from device. Send this whole message.`,
      };
    }

    const data = await response.json();

    if (data.success && data.session?.access_token) {
      await saveToken(data.session.access_token);
      if (data.session.refresh_token) {
        await SecureStore.setItemAsync(REFRESH_TOKEN_KEY, data.session.refresh_token);
      }
      if (data.user) await saveUser(data.user);
      return {
        success: true,
        user: data.user,
        token: data.session.access_token,
      };
    }

    // Backend rejected the token — surface Supabase/server reason so we can
    // disambiguate aud-mismatch vs nonce-mismatch vs other.
    const rejMsg = `[B4-DIAG] backend rejected token. status=${response.status} code=${data?.code || '?'} server_error=${data?.error || data?.detail || '?'}`;
    Sentry.captureMessage(rejMsg, { level: 'error', tags: { b4_diag: 'backend_reject' }, extra: { status: response.status, code: data?.code, server_error: data?.error || data?.detail, diagHead } });
    return {
      success: false,
      error: `${rejMsg}. token ${diagHead}. Send this whole message.`,
    };
  } catch (error: any) {
    if (error.code === 'SIGN_IN_CANCELLED') {
      return { success: false, error: 'Sign-in cancelled' };
    }
    // Diagnostic-rich error for B4 capture — REMOVE after B4 resolved.
    const thrownMsg = `[B4-DIAG] threw before fetch. code=${error?.code || '(no-code)'} msg=${error?.message || '(no-message)'} domain=${error?.domain || '(no-domain)'}`;
    Sentry.captureMessage(thrownMsg, { level: 'error', tags: { b4_diag: 'threw_before_fetch' }, extra: { errCode: error?.code, errMessage: error?.message, errDomain: error?.domain, errStack: error?.stack } });
    return {
      success: false,
      error: `${thrownMsg}. Likely: hasPlayServices/signIn() native SDK reject. Send this whole message.`,
    };
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

    // Generate cryptographic nonce (not Math.random)
    const rawNonce = Array.from(new Uint8Array(await crypto.getRandomBytesAsync(32)))
      .map((b: number) => b.toString(16).padStart(2, '0'))
      .join('');
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

    // Bundle D Phase 3 device-leg diagnostic (2026-05-25): Supabase reports
    // "Unable to detect issuer" + "malformed jwt, expected 3 parts got 1"
    // on Ahmed's iPhone. Surface the actual token shape so Xcode device log
    // can confirm whether `credential.identityToken` is the expected 3-part
    // JWT or something else (accessToken? undefined-as-string?). Remove
    // once Apple sign-in is verified GREEN.
    if (__DEV__) {
      const parts = idToken.split('.');
      console.log(
        '[APPLE-DIAG] token length:', idToken.length,
        'parts:', parts.length,
        'head:', idToken.substring(0, 30),
        'nonce-hash-len:', hashedNonce.length
      );
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
        await SecureStore.setItemAsync(REFRESH_TOKEN_KEY, data.session.refresh_token);
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
