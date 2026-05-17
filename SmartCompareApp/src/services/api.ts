/**
 * SmartCompare - API Service
 * Connects to the FastAPI backend (with iOS fixes)
 */

import axios from 'axios';
import * as ImageManipulator from 'expo-image-manipulator';
import { ComparisonResult, ImageIdentifyResult, UserPreferences } from '../types';
import { setupCertificatePinning } from './certificatePinning';

// IMPORTANT: Change this to your computer's local IP
// Find your IP: ipconfig (Windows) or ifconfig (Mac/Linux)
export const API_BASE_URL = 'https://web-production-58776.up.railway.app';

// Initialize certificate pinning (no-op in Expo Go, active in dev/prod builds)
setupCertificatePinning();

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000, // 2 minutes for image processing
});

// Auth interceptor — attach JWT to every request
api.interceptors.request.use(
  async (config) => {
    // Import here to avoid circular dependency
    const { getToken } = require('./authService');
    const token = await getToken();
    if (token) {
      config.headers = config.headers || {};
      config.headers.Authorization = `Bearer ${token}`;
    } else if (config.url?.includes('/preferences')) {
      if (__DEV__) console.warn('[API] No token available for preferences request!');
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor — auto-refresh on 401
let isRefreshing = false;
let failedQueue: Array<{ resolve: (token: string) => void; reject: (err: any) => void }> = [];

const processQueue = (error: any, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (token) prom.resolve(token);
    else prom.reject(error);
  });
  failedQueue = [];
};

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Handle USAGE_LIMIT specifically — let caller handle paywall trigger
    if (error.response?.status === 429 && error.response?.data?.detail?.code === 'USAGE_LIMIT') {
      return Promise.reject(error);
    }

    // Only retry once, and only for 401s
    if (error.response?.status !== 401 || originalRequest._retry) {
      return Promise.reject(error);
    }

    // Skip refresh for auth flow endpoints (login/register/refresh/logout)
    // but NOT for authenticated endpoints under /auth/ like /auth/preferences
    const authFlowEndpoints = ['/auth/login', '/auth/register', '/auth/refresh', '/auth/logout', '/auth/social-login'];
    if (authFlowEndpoints.some(ep => originalRequest.url?.includes(ep))) {
      return Promise.reject(error);
    }

    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        failedQueue.push({
          resolve: (token: string) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            resolve(api(originalRequest));
          },
          reject,
        });
      });
    }

    originalRequest._retry = true;
    isRefreshing = true;

    try {
      const { refreshSession, getToken } = require('./authService');
      await refreshSession();
      const newToken = await getToken();
      if (newToken) {
        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        processQueue(null, newToken);
        return api(originalRequest);
      }
      processQueue(new Error('No token after refresh'));
      return Promise.reject(error);
    } catch (refreshError) {
      const { clearSession } = require('./authService');
      await clearSession();
      processQueue(refreshError);
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  }
);

/**
 * Identify products from images via GPT-4o-mini vision, then auto-compare if 2+.
 * Uses the new /api/v1/image/identify endpoint.
 */
export async function identifyFromImages(
  imageUris: string[],
  region: string = 'bahrain'
): Promise<ImageIdentifyResult> {
  if (__DEV__) console.log('=== IDENTIFY FROM IMAGES ===');
  if (__DEV__) console.log(`${imageUris.length} image(s), region=${region}`);

  const formData = new FormData();

  for (let i = 0; i < imageUris.length; i++) {
    const uri = imageUris[i];

    // Transcode every image to JPEG — guarantees format regardless of source (HEIC, PNG, etc.)
    const manipulated = await ImageManipulator.manipulateAsync(
      uri,
      [{ resize: { width: 1024 } }],
      { format: ImageManipulator.SaveFormat.JPEG, compress: 0.8 }
    );

    formData.append('images', {
      uri: manipulated.uri,
      type: 'image/jpeg',
      name: `product_${i + 1}.jpg`,
    } as any);
  }

  // Attach auth token if available (fetch doesn't use axios interceptor)
  // Use require() to avoid circular import (authService imports api)
  const { getToken } = require('./authService');
  const token = await getToken();
  const headers: Record<string, string> = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  // Use fetch instead of Axios — Axios has known multipart issues on Android
  const response = await fetch(
    `${API_BASE_URL}/api/v1/image/identify?region=${encodeURIComponent(region)}`,
    {
      method: 'POST',
      body: formData,
      headers,
    }
  );

  if (!response.ok) {
    const errorText = await response.text();
    if (__DEV__) console.error('Identify response error:', response.status, errorText);
    throw new Error(`Server error ${response.status}: ${errorText}`);
  }

  const data: ImageIdentifyResult = await response.json();
  if (__DEV__) console.log('Identify response action:', (data as any).action);
  return data;
}

/**
 * Get comparison history
 */
export async function getComparisonHistory(limit: number = 20, offset: number = 0, search?: string) {
  const response = await api.get('/api/v1/comparisons/history', {
    params: { limit, offset, ...(search ? { search } : {}) },
  });
  return response.data;
}

/**
 * Delete a comparison from history
 */
export async function deleteComparison(comparisonId: string) {
  const response = await api.delete(`/api/v1/comparisons/${comparisonId}`);
  return response.data;
}

/**
 * Get a single comparison by ID with full payload.
 * Used by ResultsScreen when navigated from History with only an ID
 * (history list endpoint returns summary only — full_response is
 * fetched lazily on tap).
 */
export async function getComparison(comparisonId: string) {
  const response = await api.get(`/api/v1/comparisons/${comparisonId}`);
  return response.data;
}

/**
 * Health check
 */
export async function healthCheck(): Promise<boolean> {
  try {
    const response = await api.get('/health', { timeout: 5000 });
    return response.data.status === 'healthy';
  } catch {
    return false;
  }
}

/**
 * Update user display name
 */
export async function updateProfile(displayName: string): Promise<{ success: boolean; message?: string; error?: string }> {
  const response = await api.put('/api/v1/auth/profile', { display_name: displayName });
  return response.data;
}

/**
 * Update user email (sends verification to new address)
 */
export async function updateEmail(newEmail: string, currentPassword: string): Promise<{ success: boolean; message?: string; error?: string }> {
  const response = await api.put('/api/v1/auth/email', { new_email: newEmail, current_password: currentPassword });
  return response.data;
}

/**
 * Change password (requires current password)
 */
export async function changePassword(currentPassword: string, newPassword: string): Promise<{ success: boolean; message?: string; error?: string }> {
  const response = await api.put('/api/v1/auth/password', { current_password: currentPassword, new_password: newPassword });
  return response.data;
}

/**
 * Get user preferences
 */
export async function getPreferences(): Promise<UserPreferences | null> {
  try {
    const response = await api.get('/api/v1/auth/preferences');
    return response.data.preferences || null;
  } catch {
    return null;
  }
}

/**
 * Save/update user preferences
 */
export async function savePreferences(preferences: UserPreferences): Promise<{ success: boolean; error?: string }> {
  const response = await api.put('/api/v1/auth/preferences', preferences);
  return response.data;
}

/**
 * SSE streaming comparison.
 * Uses fetch + ReadableStream (EventSource not reliable in React Native).
 * Falls back to non-streaming on failure.
 */
export interface StreamCallbacks {
  onStatus?: (message: string) => void;
  onSpecs?: (data: any) => void;
  onPrices?: (data: any) => void;
  onReviews?: (data: any) => void;
  onScores?: (data: any) => void;
  onVerdict?: (data: any) => void;
  onComplete?: (data: ComparisonResult) => void;
  onError?: (error: Error) => void;
  // Bundle E § Decision 8 — settle-window SSE events.
  onFirstPaint?: (data: any) => void;
  onSettleUpdate?: (data: any) => void;
  onConfidenceUpgrade?: (data: any) => void;
  onSettleComplete?: (data: ComparisonResult) => void;
}

/**
 * Bundle B § 5.1 — dual-shape input. Callers may pass a single query string
 * (legacy `q=` shape) OR `{ product_a, product_b }` so the backend skips
 * `parse_product_query()` for higher-confidence extraction.
 */
export type StreamComparisonInput =
  | string
  | { product_a: string; product_b: string };

export function streamComparison(
  input: StreamComparisonInput,
  options?: { nocache?: boolean; selected_category?: string }
): {
  subscribe: (callbacks: StreamCallbacks) => void;
  abort: () => void;
} {
  const controller = new AbortController();

  const subscribe = (callbacks: StreamCallbacks) => {
    (async () => {
      try {
        const { getToken } = require('./authService');
        const token = await getToken();

        const params = new URLSearchParams({ region: 'bahrain' });
        if (typeof input === 'string') {
          params.set('q', input);
        } else {
          params.set('product_a', input.product_a.trim());
          params.set('product_b', input.product_b.trim());
        }
        if (options?.nocache) params.set('nocache', 'true');
        if (options?.selected_category) params.set('selected_category', options.selected_category);

        const headers: Record<string, string> = { Accept: 'text/event-stream' };
        if (token) headers['Authorization'] = `Bearer ${token}`;

        const response = await fetch(
          `${API_BASE_URL}/api/v1/text/compare/stream?${params.toString()}`,
          { method: 'GET', headers, signal: controller.signal }
        );

        if (!response.ok || !response.body) {
          throw new Error(`Stream failed: ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const parts = buffer.split('\n\n');
          buffer = parts.pop() || '';

          for (const part of parts) {
            if (!part.trim()) continue;
            const lines = part.split('\n');
            let eventType = '';
            let eventData = '';
            for (const line of lines) {
              if (line.startsWith('event: ')) eventType = line.slice(7).trim();
              else if (line.startsWith('data: ')) eventData = line.slice(6);
            }
            if (!eventType || !eventData) continue;

            try {
              const parsed = JSON.parse(eventData);
              switch (eventType) {
                case 'status': callbacks.onStatus?.(parsed.message || parsed); break;
                case 'specs': callbacks.onSpecs?.(parsed); break;
                case 'prices': callbacks.onPrices?.(parsed); break;
                case 'reviews': callbacks.onReviews?.(parsed); break;
                case 'scores': callbacks.onScores?.(parsed); break;
                case 'verdict': callbacks.onVerdict?.(parsed); break;
                case 'complete': callbacks.onComplete?.(parsed); break;
                // Bundle E § Decision 8 — settle-window events.
                case 'first_paint': callbacks.onFirstPaint?.(parsed); break;
                case 'settle_update': callbacks.onSettleUpdate?.(parsed); break;
                case 'confidence_upgrade': callbacks.onConfidenceUpgrade?.(parsed); break;
                case 'settle_complete': callbacks.onSettleComplete?.(parsed); break;
                case 'error': callbacks.onError?.(new Error(parsed.error || 'Stream error')); break;
              }
            } catch {
              // Ignore malformed JSON lines
            }
          }
        }
      } catch (err: any) {
        if (err.name === 'AbortError') return;
        // Fallback to non-streaming
        if (__DEV__) console.log('SSE failed, falling back to non-streaming:', err.message);
        try {
          const baseParams: Record<string, any> = {
            region: 'bahrain',
            selected_category: options?.selected_category,
            ...(options?.nocache && { nocache: true }),
          };
          const queryParams =
            typeof input === 'string'
              ? { q: input, ...baseParams }
              : {
                  product_a: input.product_a.trim(),
                  product_b: input.product_b.trim(),
                  ...baseParams,
                };
          const response = await api.get('/api/v1/text/compare', {
            params: queryParams,
            signal: controller.signal,
          });
          if (response.data.success) {
            callbacks.onComplete?.(response.data);
          } else {
            callbacks.onError?.(new Error(response.data.error || 'Comparison failed'));
          }
        } catch (fallbackErr: any) {
          if (fallbackErr.name !== 'AbortError' && fallbackErr.name !== 'CanceledError') {
            callbacks.onError?.(fallbackErr);
          }
        }
      }
    })();
  };

  return { subscribe, abort: () => controller.abort() };
}

/**
 * Bundle B § 5.1 — POST `{ product_a, product_b }` to /api/v1/text/compare
 * (non-streaming). Skips backend parse_product_query() for higher-confidence
 * extraction when caller has the parsed pair on hand.
 */
export interface CompareOptions {
  nocache?: boolean;
  selected_category?: string;
}

export async function compareTextPair(
  productA: string,
  productB: string,
  opts: CompareOptions = {}
): Promise<ComparisonResult> {
  const response = await api.post('/api/v1/text/compare', {
    product_a: productA.trim(),
    product_b: productB.trim(),
    region: 'bahrain',
    ...(opts.selected_category && { selected_category: opts.selected_category }),
    ...(opts.nocache && { nocache: true }),
  });
  return response.data;
}

/**
 * Submit feedback on a comparison result
 */
export async function submitFeedback(data: {
  useful: boolean;
  comparison_id?: string;
  mattered_most?: string[];
  change_suggestion?: string;
}): Promise<{ success: boolean }> {
  const response = await api.post('/api/v1/feedback', data);
  return response.data;
}

/**
 * Batch track user events (fire-and-forget)
 */
export async function trackEvents(events: Array<{
  event_type: string;
  event_data?: Record<string, any>;
  comparison_id?: string;
}>): Promise<void> {
  try {
    await api.post('/api/v1/events', { events });
  } catch {
    // Fire-and-forget: swallow errors
  }
}

/**
 * Single-event analytics helper for the Bundle B compare_entry_* taxonomy
 * (spec § 8). Wraps the batched trackEvents() so HomeScreen + TwoInputShell
 * callers don't have to construct event arrays for every fire.
 *
 * __DEV__-gated console.log lets QA capture a clean per-event log during
 * QA-6 walkthrough (plan § 4.6). NO-op in production builds — does NOT
 * ship instrumentation noise to release.
 *
 * Privacy invariant per spec § 8: event_data must never contain user-typed
 * text or pasted URLs. Only mode, booleans, timing, and source_box enum.
 * QA-6 verifies this by grepping the captured log for iPhone / Galaxy /
 * https:// patterns — any hit is a contract violation, NOT a test bug.
 */
export async function trackEvent(
  event_type: string,
  event_data?: Record<string, any>,
  comparison_id?: string,
): Promise<void> {
  if (__DEV__) {
    // eslint-disable-next-line no-console
    console.log('[analytics]', event_type, JSON.stringify(event_data || {}));
  }
  await trackEvents([{ event_type, event_data, comparison_id }]);
}

export function parseApiError(error: any): { message: string; code: string | null } {
  const data = error?.response?.data;
  if (data?.error) {
    return { message: data.error, code: data.code || null };
  }
  if (data?.detail) {
    return { message: typeof data.detail === 'string' ? data.detail : 'Invalid request', code: null };
  }
  if (error?.message) {
    return { message: error.message, code: null };
  }
  return { message: 'Something went wrong', code: null };
}

export async function shareComparison(comparisonId: string): Promise<{ share_token: string; share_url: string }> {
  const response = await api.post(`/api/v1/share/${comparisonId}`);
  return response.data;
}

// --- Cohort personalization (survey-driven) ---

export interface DemographicsPayload {
  age_group?: string;
  gender?: string;
  governorate?: string;
  language?: string;
  country?: string;
}

export interface CohortMatchSummary {
  cohort_key?: string;
  match_quality:
    | 'exact'
    | 'broadened_governorate'
    | 'broadened_language'
    | 'broadened_age'
    | 'population';
  confidence: 'high' | 'medium' | 'low';
  n: number;
  persona_label?: string;
}

export interface CohortDisplayProfile {
  persona_label: string;
  n: number;
  confidence: 'high' | 'medium' | 'low';
  modal: {
    top_deciding_factor?: string;
    second_deciding_factor?: string;
    spend_bracket?: string;
    preferred_assistance_style?: string;
    [key: string]: any;
  };
}

/**
 * Submit user demographics. Backend matches to a cohort and seeds preferences
 * (one-shot) when the user has no user_stated preferences. See backend route
 * PUT /api/v1/auth/demographics.
 */
export async function putDemographics(
  payload: DemographicsPayload
): Promise<{ success: boolean; cohort_match: CohortMatchSummary | null }> {
  const response = await api.put('/api/v1/auth/demographics', payload);
  return response.data;
}

/**
 * Fetch the user's cohort display profile for the Profile screen card.
 * Returns { display: null } when confidence < medium or user hasn't submitted
 * demographics. Network errors are swallowed and return null (best-effort UI).
 */
export async function getCohortProfile(): Promise<{
  display: CohortDisplayProfile | null;
}> {
  try {
    const response = await api.get('/api/v1/auth/cohort-profile');
    return { display: response.data?.display ?? null };
  } catch {
    return { display: null };
  }
}

/**
 * Submit acquisition attribution. Backend stores `users.attribution_source`
 * via POST /api/v1/auth/attribution (Task 8). Caller treats this as
 * fire-and-forget — onboarding never fails on this call.
 */
export type AttributionSource =
  | 'friend' | 'instagram' | 'tiktok' | 'app_store' | 'google' | 'other';

export async function saveAttribution(
  source: AttributionSource
): Promise<{ success: boolean }> {
  const response = await api.post('/api/v1/auth/attribution', { source });
  return response.data;
}

export default api;
