/**
 * Qaren - API Service
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
// R9 (Bundle D Task 1.F.1): module-scope singleton Promise so that N concurrent
// 401s share a single refreshSession() network call instead of stampeding the
// refresh endpoint. Identity-stable across coalesced callers — Promise.all on
// the cached value works.
type RefreshResult = { success: boolean; token: string | null; error?: unknown };

let refreshPromise: Promise<RefreshResult> | null = null;

async function performRefresh(): Promise<RefreshResult> {
  try {
    const { refreshSession, getToken } = require('./authService');
    await refreshSession();
    const newToken = await getToken();
    if (newToken) {
      return { success: true, token: newToken };
    }
    return { success: false, token: null, error: new Error('No token after refresh') };
  } catch (err) {
    const { clearSession } = require('./authService');
    await clearSession();
    throw err;
  }
}

function getOrStartRefresh(): Promise<RefreshResult> {
  if (refreshPromise) return refreshPromise;
  refreshPromise = performRefresh().finally(() => {
    refreshPromise = null;
  });
  return refreshPromise;
}

/** Test-only: clear the in-flight refresh Promise. Do NOT call in production. */
export function __resetRefreshMutex(): void {
  refreshPromise = null;
}

/** Test-only: trigger the dedup path and return the cached Promise. */
export function __testRefreshDedup(): Promise<RefreshResult> {
  return getOrStartRefresh();
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Handle USAGE_LIMIT specifically — let caller handle paywall trigger.
    // H2: dual-read both shapes — legacy FastAPI (detail.code) and unified
    // error format (top-level code). Keep in sync with usageService.ts.
    if (error.response?.status === 429) {
      const data = error.response?.data;
      const usageLimit =
        data?.detail?.code === 'USAGE_LIMIT' || data?.code === 'USAGE_LIMIT';
      if (usageLimit) {
        return Promise.reject(error);
      }
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

    originalRequest._retry = true;

    try {
      const result = await getOrStartRefresh();
      if (result.success && result.token) {
        originalRequest.headers.Authorization = `Bearer ${result.token}`;
        return api(originalRequest);
      }
      return Promise.reject(error);
    } catch (refreshError) {
      return Promise.reject(refreshError);
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

    // H3: detect USAGE_LIMIT on the camera path (raw fetch — no axios
    // interceptor here). Backend returns the same shapes as axios
    // endpoints: legacy { detail: { code, ... } } OR unified { code, ... }.
    // Throw a tagged error so ResultsScreen can route to Paywall instead
    // of showing the misleading "Snap one more in better light" message.
    if (response.status === 429) {
      let usageDetail: any = null;
      try {
        const data = JSON.parse(errorText);
        if (data?.detail?.code === 'USAGE_LIMIT') {
          usageDetail = data.detail;
        } else if (data?.code === 'USAGE_LIMIT') {
          usageDetail = data;
        }
      } catch {
        // Body wasn't JSON — fall through to generic error.
      }
      if (usageDetail) {
        const err: any = new Error('Usage limit reached');
        err.code = 'USAGE_LIMIT';
        err.detail = usageDetail;
        throw err;
      }
    }

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
 *
 * Backend wraps in `{success, comparison: {id, query, full_response, ...}}`;
 * unwrap to the inner `full_response` so callers get the same shape as
 * a fresh /text/compare result. Path A R2: prior code returned the
 * wrapper as-is, leaving ResultsScreen with `result.products === undefined`
 * → empty-state branch even though the row loaded fine. Ahmed flagged
 * "History still doesn't show comparison content".
 */
export async function getComparison(comparisonId: string) {
  const response = await api.get(`/api/v1/comparisons/${comparisonId}`);
  const wrapper = response.data;
  const comparison = wrapper?.comparison ?? null;
  const full = comparison?.full_response ?? null;
  if (!full) {
    throw Object.assign(new Error('Comparison payload missing'), {
      response: { status: 404, data: wrapper },
    });
  }
  return full;
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
 * Bundle D 2.F.1 (R18) — wire the 3 re-engagement sub-toggles to a
 * dedicated endpoint instead of rolling them through the full
 * /preferences body. Backend (commit `228ff63`) translates the FE-facing
 * plural keys into the DB-side singular keys (`decision_insight`,
 * `cohort_curiosity`, `decision_retrospective`) and read-modify-writes
 * `users.preferences.notification_types` while preserving every other
 * preference field. 10/min rate limit; auth required.
 *
 * Body shape (all 3 fields REQUIRED — Pydantic 422 if missing):
 *   {
 *     decision_insights: boolean,
 *     peer_decision_updates: boolean,
 *     decision_retrospectives: boolean,
 *   }
 */
export interface ReengagementSubsBody {
  decision_insights: boolean;
  peer_decision_updates: boolean;
  decision_retrospectives: boolean;
}

export async function putReengagementSubs(
  body: ReengagementSubsBody
): Promise<{ success: boolean; notification_types?: Record<string, boolean>; error?: string }> {
  const response = await api.put('/api/v1/auth/reengagement-subs', body);
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
  if (__DEV__) console.log('[analytics]', event_type, JSON.stringify(event_data || {}));
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

// ============================================================================
// Bundle D 2.5 — HomeScreen editorial sections.
// Endpoints registered at app/api/home_routes.py, auth-required (savings,
// smart-pick) / auth-optional (trending), 30-60/min.
// Each endpoint returns `{ ...payload, empty_state | threshold_met }` so
// callers can hide the corresponding UI section silently.
// ============================================================================

export interface HomeSavingsResponse {
  savings_bhd: number;
  decisions_count: number;
  threshold_met: boolean;
}

export async function getHomeSavings(): Promise<HomeSavingsResponse | null> {
  try {
    const response = await api.get('/api/v1/home/savings');
    return response.data;
  } catch {
    return null;
  }
}

export interface HomeSmartPickItem {
  comparison_id: string;
  winner_name: string;
  runner_up_name: string;
  winner_price_bhd: number | null;
  runner_up_price_bhd: number | null;
  reason_key: string;
  reason_params: Record<string, string>;
  // --- Bundle E B4.3b extensions (per HomeScreen.jsx:438-501) ---
  // ALL nullable — render-site MUST hide-the-surround when null per the
  // null-hide-surround rule (don't fabricate, don't render the eyebrow /
  // chip / sub-line / verdict caption when its source field is null).
  /** Category eyebrow pill (e.g. "Electronics", "Skincare"). Nullable. */
  category: string | null;
  /** Server-computed relative-time string (e.g. "Updated 30m ago",
   *  "Today"). NEVER raw ISO — clock-skew avoided. Always non-null when
   *  smart_pick itself is non-null (backend derives it from
   *  comparisons.created_at). */
  updated_at: string;
  /** Winning product's spec sub-line (e.g. "128GB"). Nullable. */
  winner_sub: string | null;
  /** Runner-up product's spec sub-line (e.g. "256GB"). Nullable. */
  runner_up_sub: string | null;
  /** Short verdict sentence (≤160 chars, no scary vocab). Nullable. */
  verdict_short: string | null;
  /**
   * Optional precomputed tone/sub conveniences. Backend MAY populate;
   * frontend falls back to deriveTone(winner_name) for tone + the
   * winner_sub / runner_up_sub fields for spec lines when these are
   * absent. Exists at the type level so the Bundle E contract test
   * (HomeScreen.bundleE.contract.test.tsx § 4) recognizes the new shape.
   */
  tone?: string;
  sub?: string;
}

export interface HomeSmartPickResponse {
  smart_pick: HomeSmartPickItem | null;
  empty_state: boolean;
  cta_text_key?: string;
}

export async function getHomeSmartPick(): Promise<HomeSmartPickResponse> {
  try {
    const response = await api.get('/api/v1/home/smart-pick');
    return response.data;
  } catch {
    return { smart_pick: null, empty_state: true };
  }
}

export interface HomeTrendingItem {
  // --- Bundle E B4.3a — JSX-wins pre-split shape (per HomeScreen.jsx:609-615) ---
  /** Category tag eyebrow (e.g. "Electronics", "Skincare", "Supplements"). */
  tag: string;
  /** Pre-split product A name. Backend splits the curated query by " vs " so
   *  frontend never does fragile string parsing. */
  a: string;
  /** Pre-split product B name. */
  b: string;
  /** Comparison view count (tabular-nums "142 ↗" rendered by consumer). */
  count: number;
  // --- Legacy fields surviving one release cycle for backwards-compat ---
  /** @deprecated Use `a`/`b` split. Will be removed after Bundle F. */
  query: string;
  /** @deprecated Use `count` (same value). Will be removed after Bundle F. */
  view_count: number;
  /** Region tag carried through for upstream filtering. */
  region: string;
}

export interface HomeTrendingResponse {
  trending: HomeTrendingItem[];
  region: string;
}

export async function getHomeTrending(region?: string): Promise<HomeTrendingResponse> {
  try {
    const params = region ? { region } : {};
    const response = await api.get('/api/v1/home/trending', { params });
    return response.data;
  } catch {
    return { trending: [], region: 'bahrain' };
  }
}

// ============================================================================
// Bundle D 2.6 — ProfileScreen editorial sections.
// Endpoints registered at app/api/profile_routes.py, all auth-required, 30/min.
// Each endpoint returns `{ ...payload, empty_state: bool }` so callers can
// hide the corresponding UI section silently when there's nothing meaningful
// to render (consistent with /home/savings hide gate pattern).
// ============================================================================

export interface RecentDecisionItem {
  comparison_id: string;
  winner_name: string;
  runner_up_name: string;
  created_at: string;
}

export interface RecentDecisionsResponse {
  recent: RecentDecisionItem[];
  empty_state: boolean;
  cta_text_key?: string;
}

export async function getProfileRecentDecisions(): Promise<RecentDecisionsResponse> {
  try {
    const response = await api.get('/api/v1/profile/recent-decisions');
    return response.data;
  } catch {
    // Silent hide on any failure — UI must not surface a scary error here.
    return { recent: [], empty_state: true };
  }
}

export interface MonthlyStatsResponse {
  month: string;
  decisions_count: number;
  savings_bhd: number;
  bonus_credits_this_month: number;
  threshold_met: boolean;
}

export async function getProfileMonthlyStats(): Promise<MonthlyStatsResponse | null> {
  try {
    const response = await api.get('/api/v1/profile/monthly-stats');
    return response.data;
  } catch {
    return null;
  }
}

export interface WeightedPriority {
  key: string;
  label_key: string;
  weight: number;
}

export interface PrioritiesWeightedResponse {
  priorities: WeightedPriority[];
  empty_state: boolean;
}

export async function getProfilePrioritiesWeighted(): Promise<PrioritiesWeightedResponse> {
  try {
    const response = await api.get('/api/v1/profile/priorities-weighted');
    return response.data;
  } catch {
    return { priorities: [], empty_state: true };
  }
}

export default api;
