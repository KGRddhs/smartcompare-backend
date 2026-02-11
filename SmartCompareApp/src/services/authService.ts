/**
 * Authentication Service - Supabase Auth
 * Handles login, register, logout, and session management
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import api from './api';

export interface User {
  id: string;
  email: string;
  created_at?: string;
}

export interface AuthResponse {
  success: boolean;
  user?: User;
  token?: string;
  error?: string;
}

const USER_STORAGE_KEY = '@smartcompare_user';
const TOKEN_STORAGE_KEY = '@smartcompare_token';

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
    const token = await getToken();
    if (!token) {
      return { success: false, error: 'No token found' };
    }

    const response = await api.post('/api/v1/auth/refresh', {}, {
      headers: { Authorization: `Bearer ${token}` }
    });

    if (response.data.user) {
      await saveUser(response.data.user);
      if (response.data.session?.access_token) {
        await saveToken(response.data.session.access_token);
      }
      return {
        success: true,
        user: response.data.user,
        token: response.data.session?.access_token,
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
async function clearSession(): Promise<void> {
  try {
    await AsyncStorage.multiRemove([USER_STORAGE_KEY, TOKEN_STORAGE_KEY]);
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
 * Verify auth status - alias for isLoggedIn
 * Used by App.tsx to check auth state
 */
export async function verifyAuth(): Promise<boolean> {
  return await isLoggedIn();
}
