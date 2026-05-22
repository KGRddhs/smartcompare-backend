/**
 * Qaren - Usage Service
 * Fetches usage status from backend and provides paywall trigger logic.
 */

import api from './api';

export interface UsageStatus {
  tier: 'free' | 'premium';
  used: {
    daily: number;
    monthly: number;
    lifetime: number;
  };
  limits: {
    daily: number;
    monthly: number;
    lifetime_free: number;
  };
  remaining: {
    daily: number;
    monthly: number;
  };
}

export interface UsageLimitError {
  code: 'USAGE_LIMIT';
  tier: string;
  reason: string;
  remaining: {
    daily: number;
    monthly: number;
    lifetime_free: number;
  };
}

export async function getUsageStatus(): Promise<UsageStatus | null> {
  try {
    const response = await api.get('/api/v1/usage/status');
    return response.data;
  } catch {
    return null;
  }
}

// H2 fix: backend ships two error shapes during the unified-error
// migration:
//   legacy FastAPI:  { detail: { code: 'USAGE_LIMIT', tier, reason, ... } }
//   unified:         { success: false, error, code: 'USAGE_LIMIT', ... }
// We dual-read both so the paywall fires on every endpoint regardless
// of which shape it returns. Drop the legacy path once all routes are
// migrated to the unified format.
function _usageLimitPayload(error: any): any | null {
  const data = error?.response?.data;
  if (!data) return null;
  if (data?.detail?.code === 'USAGE_LIMIT') return data.detail;
  if (data?.code === 'USAGE_LIMIT') return data;
  return null;
}

export function isUsageLimitError(error: any): boolean {
  return _usageLimitPayload(error) !== null;
}

export function getUsageLimitDetail(error: any): UsageLimitError | null {
  const payload = _usageLimitPayload(error);
  return payload ? (payload as UsageLimitError) : null;
}

export function formatUsageMessage(status: UsageStatus): string {
  if (status.tier === 'free') {
    return `${status.used.monthly} of ${status.limits.monthly} comparisons used this month`;
  }
  return `${status.used.monthly} of ${status.limits.monthly} comparisons used this month (Premium)`;
}
