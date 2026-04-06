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

export function isUsageLimitError(error: any): boolean {
  const detail = error?.response?.data?.detail;
  return detail?.code === 'USAGE_LIMIT';
}

export function getUsageLimitDetail(error: any): UsageLimitError | null {
  const detail = error?.response?.data?.detail;
  if (detail?.code === 'USAGE_LIMIT') {
    return detail as UsageLimitError;
  }
  return null;
}

export function formatUsageMessage(status: UsageStatus): string {
  if (status.tier === 'free') {
    return `${status.used.monthly} of ${status.limits.monthly} comparisons used this month`;
  }
  return `${status.used.monthly} of ${status.limits.monthly} comparisons used this month (Premium)`;
}
