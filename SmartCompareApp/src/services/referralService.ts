/**
 * Referral system frontend service.
 *
 * Wraps the backend referral endpoints and normalizes the FastAPI nested
 * `detail.{code,error}` payload into a flat ReferralError that components
 * can switch on without re-reaching into axios internals.
 *
 * Endpoints touched:
 *   POST /api/v1/referrals/share          (B2.1)
 *   GET  /api/v1/referrals/status         (B2.2)
 *   GET  /api/v1/referrals/invite/:token  (B3.1, no-auth)
 *   POST /api/v1/referrals/invite/:token/quiz (B3.4, no-auth)
 */

import axios from 'axios';
import { api } from './api';

export type ShareTarget =
  | 'whatsapp'
  | 'copy'
  | 'x'
  | 'telegram'
  | 'snapchat'
  | 'other';

export interface CreateShareInput {
  comparison_id: string;
  share_target: ShareTarget;
  device_fingerprint_hash?: string;
}

export interface CreateShareResult {
  success: true;
  invite_id: string;
  share_link: string;
  weekly_invites_used: number;
  weekly_invites_remaining: number;
  // Backend may add more keys; keep open for extension
  [key: string]: unknown;
}

export interface ReferralStatus {
  referral_code: string;
  weekly_invites_used: number;
  weekly_invites_remaining: number;
  monthly_bonus_comparisons: number;
  monthly_bonus_cap: number;
  deep_review_credits_available: number;
  total_lifetime_redemptions: number;
}

export class ReferralError extends Error {
  code: string;
  status: number | null;
  constructor(message: string, code: string, status: number | null) {
    super(message);
    this.name = 'ReferralError';
    this.code = code;
    this.status = status;
  }
}

function normalizeError(err: unknown): ReferralError {
  if (axios.isAxiosError(err)) {
    const status = err.response?.status ?? null;
    const data = err.response?.data as { detail?: any; error?: string; code?: string } | undefined;
    // FastAPI HTTPException nests {code, error} under data.detail
    const detail = data?.detail;
    if (detail && typeof detail === 'object') {
      return new ReferralError(
        detail.error ?? 'Request failed',
        detail.code ?? 'UNKNOWN',
        status
      );
    }
    if (data?.error) {
      return new ReferralError(data.error, data.code ?? 'UNKNOWN', status);
    }
    if (typeof detail === 'string') {
      return new ReferralError(detail, 'UNKNOWN', status);
    }
    return new ReferralError(err.message ?? 'Network error', 'NETWORK', status);
  }
  if (err instanceof Error) {
    return new ReferralError(err.message, 'UNKNOWN', null);
  }
  return new ReferralError('Unknown error', 'UNKNOWN', null);
}

export async function createShare(input: CreateShareInput): Promise<CreateShareResult> {
  try {
    const response = await api.post('/api/v1/referrals/share', input);
    return response.data as CreateShareResult;
  } catch (err) {
    throw normalizeError(err);
  }
}

export async function getReferralStatus(): Promise<ReferralStatus> {
  try {
    const response = await api.get('/api/v1/referrals/status');
    return response.data as ReferralStatus;
  } catch (err) {
    throw normalizeError(err);
  }
}

export interface InviteResolution {
  invite_id: string;
  referrer_display_name: string;
  comparison: any; // sanitized — preferences/budget stripped server-side
  cohort_match: { match_quality: string; language?: string; governorate?: string } | null;
}

export async function resolveInvite(args: { share_token: string; ref: string }): Promise<InviteResolution> {
  try {
    const response = await api.get(`/api/v1/referrals/invite/${encodeURIComponent(args.share_token)}`, {
      params: { ref: args.ref },
    });
    return response.data as InviteResolution;
  } catch (err) {
    throw normalizeError(err);
  }
}

export interface InviteeQuizInput {
  priority: string;
  budget: string;
  brand_attitude: string;
  non_negotiable?: string;
}

export async function submitInviteeQuiz(
  share_token: string,
  input: InviteeQuizInput
): Promise<unknown> {
  try {
    const response = await api.post(
      `/api/v1/referrals/invite/${encodeURIComponent(share_token)}/quiz`,
      input
    );
    return response.data;
  } catch (err) {
    throw normalizeError(err);
  }
}
