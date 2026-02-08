/**
 * SmartCompare - Auth Service
 * Handles authentication with Supabase via our backend
 */

import * as SecureStore from 'expo-secure-store';
import api from './api';

const TOKEN_KEY = 'smartcompare_access_token';
const REFRESH_KEY = 'smartcompare_refresh_token';
const USER_KEY = 'smartcompare_user';

export interface User {
  id: string;
  email: string;
  subscription_tier?: string;
}

export interface AuthSession {
  access_token: string;
  refresh_token: string;
  expires_at?: number;
}

export interface AuthResponse {
  success: boolean;
  user?: User;
  session?: AuthSession;
  message?: string;
  error?: string;
}

// ============================================
// Token Storage
// ============================================

export async function saveTokens(session: AuthSession): Promise<void> {
  try {
    if (session.access_token) {
      await SecureStore.setItemAsync(TOKEN_KEY, session.access_token);
    }
    if (session.refresh_token) {
      await SecureStore.setItemAsync(REFRESH_KEY, session.refresh_token);
    }
  } catch (error) {
    console.error('Error saving tokens:', error);
  }
}

export async function getAccessToken(): Promise<string | null> {
  try {
    return await SecureStore.getItemAsync(TOKEN_KEY);
  } catch (error) {
    console.error('Error getting access token:', error);
    return null;
  }
}

export async function getRefreshToken(): Promise<string | null> {
  try {
    return await SecureStore.getItemAsync(REFRESH_KEY);
  } catch (error) {
    console.error('Error getting refresh token:', error);
    return null;
  }
}

export async function clearTokens(): Promise<void> {
  try {
    await SecureStore.deleteItemAsync(TOKEN_KEY);
    await SecureStore.deleteItemAsync(REFRESH_KEY);
    await SecureStore.deleteItemAsync(USER_KEY);
  } catch (error) {
    console.error('Error clearing tokens:', error);
  }
}

export async function saveUser(user: User): Promise<void> {
  try {
    await SecureStore.setItemAsync(USER_KEY, JSON.stringify(user));
  } catch (error) {
    console.error('Error saving user:', error);
  }
}

export async function getSavedUser(): Promise<User | null> {
  try {
    const userJson = await SecureStore.getItemAsync(USER_KEY);
    return userJson ? JSON.parse(userJson) : null;
  } catch (error) {
    console.error('Error getting saved user:', error);
    return null;
  }
}

// ============================================
// Auth API Calls
// ============================================

export async function register(email: string, password: string): Promise<AuthResponse> {
  try {
    const response = await api.post<AuthResponse>('/api/v1/auth/register', {
      email,
      password,
    });

    if (response.data.success && response.data.session) {
      await saveTokens(response.data.session);
      if (response.data.user) {
        await saveUser(response.data.user);
      }
    }

    return response.data;
  } catch (error: any) {
    const message = error.response?.data?.detail || error.message || 'Registration failed';
    return { success: false, error: message };
  }
}

export async function login(email: string, password: string): Promise<AuthResponse> {
  try {
    const response = await api.post<AuthResponse>('/api/v1/auth/login', {
      email,
      password,
    });

    if (response.data.success && response.data.session) {
      await saveTokens(response.data.session);
      if (response.data.user) {
        await saveUser(response.data.user);
      }
    }

    return response.data;
  } catch (error: any) {
    const message = error.response?.data?.detail || error.message || 'Login failed';
    return { success: false, error: message };
  }
}

export async function logout(): Promise<void> {
  try {
    const token = await getAccessToken();
    if (token) {
      await api.post('/api/v1/auth/logout', {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
    }
  } catch (error) {
    console.error('Logout API error:', error);
  } finally {
    await clearTokens();
  }
}

export async function refreshSession(): Promise<boolean> {
  try {
    const refreshToken = await getRefreshToken();
    if (!refreshToken) return false;

    const response = await api.post<AuthResponse>('/api/v1/auth/refresh', {
      refresh_token: refreshToken,
    });

    if (response.data.success && response.data.session) {
      await saveTokens(response.data.session);
      return true;
    }

    return false;
  } catch (error) {
    console.error('Session refresh error:', error);
    return false;
  }
}

export async function verifyAuth(): Promise<User | null> {
  try {
    const token = await getAccessToken();
    if (!token) return null;

    const response = await api.get('/api/v1/auth/verify', {
      headers: { Authorization: `Bearer ${token}` }
    });

    if (response.data.success && response.data.user) {
      await saveUser(response.data.user);
      return response.data.user;
    }

    return null;
  } catch (error: any) {
    // Token might be expired, try to refresh
    if (error.response?.status === 401) {
      const refreshed = await refreshSession();
      if (refreshed) {
        return verifyAuth(); // Retry with new token
      }
    }
    return null;
  }
}

export async function getCurrentUser(): Promise<User | null> {
  try {
    const token = await getAccessToken();
    if (!token) return null;

    const response = await api.get('/api/v1/auth/me', {
      headers: { Authorization: `Bearer ${token}` }
    });

    if (response.data.success && response.data.user) {
      return response.data.user;
    }

    return null;
  } catch (error) {
    console.error('Get current user error:', error);
    return null;
  }
}

export async function requestPasswordReset(email: string): Promise<AuthResponse> {
  try {
    const response = await api.post<AuthResponse>('/api/v1/auth/password-reset', {
      email,
    });
    return response.data;
  } catch (error: any) {
    return { success: true, message: 'If an account exists, a reset link has been sent.' };
  }
}

// ============================================
// Auth Header Helper
// ============================================

export async function getAuthHeader(): Promise<{ Authorization: string } | {}> {
  const token = await getAccessToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}
