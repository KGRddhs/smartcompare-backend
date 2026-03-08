/**
 * SmartCompare - API Service
 * Connects to the FastAPI backend (with iOS fixes)
 */

import axios from 'axios';
import * as ImageManipulator from 'expo-image-manipulator';
import { ComparisonResult, ImageIdentifyResult, RateLimitStatus, SubscriptionStatus, UserPreferences } from '../types';

// IMPORTANT: Change this to your computer's local IP
// Find your IP: ipconfig (Windows) or ifconfig (Mac/Linux)
export const API_BASE_URL = 'https://smartcompare-backend-production.up.railway.app';

const api = axios.create({
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

    // Only retry once, and only for 401s
    if (error.response?.status !== 401 || originalRequest._retry) {
      return Promise.reject(error);
    }

    // Skip refresh for auth endpoints themselves
    if (originalRequest.url?.includes('/auth/')) {
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
 * Compare products from images (iOS & Android compatible)
 */
export async function compareProducts(
  imageUris: string[],
  country: string = 'Bahrain'
): Promise<ComparisonResult> {
  
  console.log('=== COMPARE PRODUCTS ===');
  console.log('Image URIs:', imageUris);
  
  const formData = new FormData();

  // Add images to form data
  for (let i = 0; i < imageUris.length; i++) {
    const uri = imageUris[i];
    console.log(`Processing image ${i + 1}: ${uri}`);
    
    // Get file name and extension
    const uriParts = uri.split('/');
    let fileName = uriParts[uriParts.length - 1];
    
    // Handle iOS photo library URIs
    if (uri.includes('ph://')) {
      fileName = `photo_${i + 1}.jpg`;
    }
    
    // Get extension
    const extensionMatch = fileName.match(/\.([^.]+)$/);
    let extension = extensionMatch ? extensionMatch[1].toLowerCase() : 'jpg';
    
    // Normalize extension
    if (extension === 'jpeg') extension = 'jpg';
    if (extension === 'heic' || extension === 'heif') extension = 'jpg';
    
    // Determine MIME type
    let mimeType = 'image/jpeg';
    if (extension === 'png') {
      mimeType = 'image/png';
    } else if (extension === 'webp') {
      mimeType = 'image/webp';
    }
    
    const finalFileName = `product_${i + 1}.${extension}`;
    
    console.log(`  -> filename: ${finalFileName}, type: ${mimeType}`);
    
    // Append to form data (React Native style)
    formData.append('images', {
      uri: uri,
      type: mimeType,
      name: finalFileName,
    } as any);
  }

  console.log('Sending request to:', `${API_BASE_URL}/api/v1/compare`);
  
  try {
    const response = await api.post<ComparisonResult>(
      `/api/v1/compare?country=${encodeURIComponent(country)}`,
      formData,
      {
        // Don't set Content-Type — let FormData set it with correct boundary
        transformRequest: (data) => data,
      }
    );
    
    console.log('Response status:', response.status);
    console.log('Response data:', JSON.stringify(response.data, null, 2));
    
    return response.data;
  } catch (error: any) {
    console.log('=== REQUEST ERROR ===');
    console.log('Error message:', error.message);
    
    if (error.response) {
      console.log('Response status:', error.response.status);
      console.log('Response data:', JSON.stringify(error.response.data, null, 2));
    }
    
    throw error;
  }
}

/**
 * Identify products from images via GPT-4o-mini vision, then auto-compare if 2+.
 * Uses the new /api/v1/image/identify endpoint.
 */
export async function identifyFromImages(
  imageUris: string[],
  region: string = 'bahrain'
): Promise<ImageIdentifyResult> {
  console.log('=== IDENTIFY FROM IMAGES ===');
  console.log(`${imageUris.length} image(s), region=${region}`);

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
    console.error('Identify response error:', response.status, errorText);
    throw new Error(`Server error ${response.status}: ${errorText}`);
  }

  const data: ImageIdentifyResult = await response.json();
  console.log('Identify response action:', (data as any).action);
  return data;
}

/**
 * Quick compare without images (text-based)
 */
export async function quickCompare(
  products: { brand: string; name: string; size?: string }[],
  country: string = 'Bahrain'
): Promise<ComparisonResult> {
  const response = await api.post<ComparisonResult>('/api/v1/compare/quick', {
    products,
    country,
  });

  return response.data;
}

/**
 * Get rate limit status
 */
export async function getRateLimitStatus(): Promise<RateLimitStatus> {
  const response = await api.get<RateLimitStatus>('/api/v1/rate-limit/status');
  return response.data;
}

/**
 * Get subscription status
 */
export async function getSubscriptionStatus(): Promise<SubscriptionStatus> {
  const response = await api.get<SubscriptionStatus>('/api/v1/subscription/status');
  return response.data;
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
 * Debug function to test image upload
 */
export async function debugUpload(imageUris: string[]): Promise<any> {
  console.log('=== DEBUG UPLOAD ===');
  
  const formData = new FormData();

  for (let i = 0; i < imageUris.length; i++) {
    const uri = imageUris[i];
    console.log(`Image ${i + 1} URI: ${uri}`);
    
    formData.append('images', {
      uri: uri,
      type: 'image/jpeg',
      name: `test_${i + 1}.jpg`,
    } as any);
  }

  const response = await api.post('/api/v1/debug/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  
  console.log('Debug response:', JSON.stringify(response.data, null, 2));
  return response.data;
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
export async function updateEmail(newEmail: string): Promise<{ success: boolean; message?: string; error?: string }> {
  const response = await api.put('/api/v1/auth/email', { new_email: newEmail });
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
}

export function streamComparison(
  query: string,
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

        const params = new URLSearchParams({ q: query, region: 'bahrain' });
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
        console.log('SSE failed, falling back to non-streaming:', err.message);
        try {
          const response = await api.get('/api/v1/text/compare', {
            params: {
              q: query,
              region: 'bahrain',
              selected_category: options?.selected_category,
              ...(options?.nocache && { nocache: true }),
            },
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

export default api;
