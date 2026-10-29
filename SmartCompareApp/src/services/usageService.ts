/**
 * Qaren - Usage Service
 * Fetches usage status from backend and provides paywall trigger logic.
 */

import api from './api';
import { withRequestContext } from './requestContext';

/**
 * S81-08 (RULINGS_S81_08 R-S08-2): the axis a reset time applies to, as the
 * server (S81-09) names it; the client shows a reset time only for 'daily' /
 * 'device_daily'.
 */
export type UsageScope = 'daily' | 'device_daily' | 'monthly' | 'lifetime';

export interface UsageStatus {
  tier: 'free' | 'premium';
  used: {
    daily: number;
    monthly: number;
    // R-S08-13: optional, so a status without the lifetime counter is still read.
    lifetime?: number;
  };
  limits: {
    daily: number;
    monthly: number;
    lifetime_free: number;
    // Effective monthly cap breakdown (get_usage_status, usage_service.py).
    // Optional so an older backend that omits them degrades gracefully —
    // useComparisonCounter reads monthly_bonus for the compare gate.
    monthly_base?: number;
    monthly_bonus?: number;
  };
  remaining: {
    daily: number;
    monthly: number;
    lifetime_free?: number;
  };
  // S81-08 (R-S08-2): optional, sent by S81-09; absent on today's server.
  resets_at?: string;
  counted_scope?: UsageScope;
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
  // S81-08 (R-S08-2 / R-S08-14): optional reset fields of the 429 (S81-09).
  resets_at?: string;
  retry_after_seconds?: number;
  retry_after?: number;
  scope?: UsageScope;
}

export async function getUsageStatus(): Promise<UsageStatus | null> {
  try {
    // S81-08 (R-S08-5): a metered read, so it carries the device and consent headers.
    const response = await api.get('/api/v1/usage/status', withRequestContext());
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
