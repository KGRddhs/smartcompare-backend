/**
 * Bundle E canonical mock fixtures for the 8 S1 surfaces.
 *
 * Frozen against the backend route source after the JSX-wins reshape sweep:
 *   - /home/savings        → app/api/home_routes.py:114 (Bundle D)
 *   - /home/smart-pick     → app/api/home_routes.py:430 (Bundle E B4.3b, commit 3bb31bd)
 *   - /home/trending       → app/api/home_routes.py:658 (Bundle E B4.3a, commit dca8067)
 *   - /profile/recent-decisions  → app/api/profile_routes.py:112
 *   - /profile/monthly-stats     → app/api/profile_routes.py:218
 *   - /profile/priorities-weighted → app/api/profile_routes.py:388 (Path A R2, 4aa9cff)
 *   - /auth/social-login         → app/api/auth_routes.py:656 + auth_service.py:302
 *   - /comparisons (history list) → app/api/history_routes.py
 *
 * Usage in a test:
 *   import { mockHomeTrendingResponse } from '../fixtures/bundleE-endpoint-mocks';
 *   jest.mock('../../src/services/api', () => ({
 *     getHomeTrending: jest.fn().mockResolvedValue(mockHomeTrendingResponse),
 *   }));
 *
 * Each fixture exports BOTH "happy" payload + the "empty_state" hide gate
 * payload where the route has one, so screen tests can exercise both
 * branches without re-typing the shape.
 */

// =============================================================================
// /home/savings — Bundle D pattern, no Bundle E reshape
// =============================================================================

export const mockHomeSavingsBelowThreshold = {
  savings_bhd: 0,
  decisions_count: 1,
  threshold_met: false, // Frontend HIDES the banner
};

export const mockHomeSavingsAboveThreshold = {
  savings_bhd: 73,
  decisions_count: 12,
  threshold_met: true,
};

// =============================================================================
// /home/smart-pick — Bundle E B4.3b extension fields (3bb31bd)
// Shipped shape carries BOTH legacy keys (winner_name, runner_up_name,
// winner_price_bhd, runner_up_price_bhd, reason_key, reason_params,
// comparison_id) AND new extension keys (category, updated_at, winner_sub,
// runner_up_sub, verdict_short). Legacy survives one release cycle.
// =============================================================================

export const mockHomeSmartPickReturningUser = {
  smart_pick: {
    // Legacy fields
    comparison_id: '11111111-aaaa-bbbb-cccc-222222222222',
    winner_name: 'Apple iPhone 15',
    runner_up_name: 'Samsung Galaxy S24',
    winner_price_bhd: 350,
    runner_up_price_bhd: 320,
    reason_key: 'home.smart_pick.reason.priority_match',
    reason_params: { priority: 'quality' },
    // Bundle E extension fields
    category: 'electronics',
    updated_at: '2026-05-26T14:00:00+00:00',
    winner_sub: '128GB · A17 Pro',
    runner_up_sub: '256GB · Snapdragon 8 Gen 3',
    verdict_short: 'Sharper camera, quieter system on the iPhone.',
  },
  empty_state: false,
};

export const mockHomeSmartPickEmptyState = {
  smart_pick: null,
  empty_state: true,
  cta_text_key: 'home.smart_pick.empty_cta',
};

export const mockHomeSmartPickExtensionFieldsNull = {
  // Bundle E test_extension_fields_null_when_data_absent contract — when
  // backend can't compute a sub or verdict_short, the keys are present but null.
  smart_pick: {
    comparison_id: '33333333-cccc-dddd-eeee-444444444444',
    winner_name: 'NOW Foods Vitamin D3',
    runner_up_name: 'Solgar Vitamin D3',
    winner_price_bhd: 5.2,
    runner_up_price_bhd: 6.1,
    reason_key: 'home.smart_pick.reason.recent_winner',
    reason_params: {},
    category: 'supplements',
    updated_at: '2026-05-25T08:00:00+00:00',
    winner_sub: null,
    runner_up_sub: null,
    verdict_short: null,
  },
  empty_state: false,
};

// =============================================================================
// /home/trending — Bundle E B4.3a pre-split (dca8067)
// Each row carries NEW fields (tag, a, b, count) + LEGACY (query, view_count,
// region) for one release cycle. The JSX renders [tag pill] [a] vs [b] [count].
// =============================================================================

export const mockHomeTrendingBahrain = {
  trending: [
    {
      // New shape (JSX-wins)
      tag: 'Electronics',
      a: 'iPhone 15',
      b: 'Galaxy S24',
      count: 142,
      // Legacy compat
      query: 'iPhone 15 vs Galaxy S24',
      view_count: 142,
      region: 'bahrain',
    },
    {
      tag: 'Skincare',
      a: 'CeraVe Cleanser',
      b: 'La Roche-Posay Toleriane',
      count: 87,
      query: 'CeraVe Cleanser vs La Roche-Posay Toleriane',
      view_count: 87,
      region: 'bahrain',
    },
    {
      tag: 'Supplements',
      a: 'NOW Foods Magnesium',
      b: 'Doctor\'s Best Magnesium',
      count: 53,
      query: 'NOW Foods Magnesium vs Doctor\'s Best Magnesium',
      view_count: 53,
      region: 'bahrain',
    },
  ],
  region: 'bahrain',
};

export const mockHomeTrendingFallbackRegion = {
  trending: [],
  region: 'bahrain', // Fallback when an unrecognized region requested
};

// =============================================================================
// /profile/recent-decisions
// =============================================================================

export const mockProfileRecentDecisions = {
  recent: [
    {
      comparison_id: '55555555-aaaa-bbbb-cccc-666666666666',
      winner_name: 'Apple iPhone 15',
      runner_up_name: 'Samsung Galaxy S24',
      created_at: '2026-05-26T10:30:00+00:00',
    },
    {
      comparison_id: '77777777-bbbb-cccc-dddd-888888888888',
      winner_name: 'CeraVe Cleanser',
      runner_up_name: 'La Roche-Posay Toleriane',
      created_at: '2026-05-25T16:45:00+00:00',
    },
    {
      comparison_id: '99999999-cccc-dddd-eeee-000000000000',
      winner_name: 'AirPods Pro 2',
      runner_up_name: 'Galaxy Buds 3 Pro',
      created_at: '2026-05-24T09:15:00+00:00',
    },
  ],
  empty_state: false,
};

export const mockProfileRecentDecisionsEmpty = {
  recent: [],
  empty_state: true,
  cta_text_key: 'profile.recent_decisions.empty_cta',
};

// =============================================================================
// /profile/monthly-stats
// =============================================================================

export const mockProfileMonthlyStatsAboveThreshold = {
  month: '2026-05',
  decisions_count: 12,
  savings_bhd: 73,
  bonus_credits_this_month: 5,
  threshold_met: true,
};

export const mockProfileMonthlyStatsBelowThreshold = {
  month: '2026-05',
  decisions_count: 1,
  savings_bhd: 0,
  bonus_credits_this_month: 0,
  threshold_met: false, // Frontend hides the strip
};

// =============================================================================
// /profile/priorities-weighted — Path A R2 (4aa9cff) Hamilton sum=100
// =============================================================================

export const mockProfilePrioritiesWeightedTypical = {
  // Hamilton largest-remainder ALWAYS sums to exactly 100 (B3.1 contract)
  priorities: [
    { key: 'camera_quality', label_key: 'priorities.camera_quality', weight: 41 },
    { key: 'battery_life', label_key: 'priorities.battery_life', weight: 33 },
    { key: 'build_quality', label_key: 'priorities.build_quality', weight: 26 },
  ],
  empty_state: false,
};

export const mockProfilePrioritiesWeightedEqual = {
  // Three equal weights → Hamilton {34, 33, 33}
  priorities: [
    { key: 'quality', label_key: 'priorities.quality', weight: 34 },
    { key: 'price', label_key: 'priorities.price', weight: 33 },
    { key: 'durable', label_key: 'priorities.durable', weight: 33 },
  ],
  empty_state: false,
};

export const mockProfilePrioritiesWeightedEmpty = {
  priorities: [],
  empty_state: true,
};

// =============================================================================
// /auth/social-login — B4 Google + Apple
// =============================================================================

export const VALID_GOOGLE_JWT_3SEG =
  'eyJhbGciOiJSUzI1NiIsImtpZCI6IjEyMyJ9' +
  '.eyJpc3MiOiJodHRwczovL2FjY291bnRzLmdvb2dsZS5jb20iLCJzdWIiOiIxIn0' +
  '.sig-placeholder-not-verified-in-mocked-flow';

export const VALID_APPLE_JWT_3SEG =
  'eyJhbGciOiJSUzI1NiIsImtpZCI6IkFCQyJ9' +
  '.eyJpc3MiOiJodHRwczovL2FwcGxlaWQuYXBwbGUuY29tIiwic3ViIjoiMSJ9' +
  '.sig-placeholder';

export const mockSocialLoginGoogleSuccess = {
  success: true,
  user: {
    id: '00000000-0000-0000-0000-000000000001',
    email: 'u@gmail.com',
    preferences_completed: false,
  },
  session: {
    access_token: 'supabase-access-token',
    refresh_token: 'supabase-refresh-token',
    expires_at: 1234567890,
  },
  message: 'Signed in with google',
};

export const mockSocialLoginAppleSuccess = {
  success: true,
  user: {
    id: '00000000-0000-0000-0000-000000000002',
    email: 'u@privaterelay.appleid.com',
    preferences_completed: true,
  },
  session: {
    access_token: 'apple-supabase-token',
    refresh_token: 'apple-refresh',
    expires_at: 1234567899,
  },
  message: 'Signed in with apple',
};

export const mockSocialLoginInvalidToken = {
  success: false,
  error: 'Invalid id_token (not a JWT)',
};

// =============================================================================
// /comparisons (history list) — schema_version=2 filtered list
// =============================================================================

export const mockHistoryList = {
  comparisons: [
    {
      id: 'cccccccc-1111-2222-3333-444444444444',
      product_names: ['Apple iPhone 15', 'Samsung Galaxy S24'],
      schema_version: 2,
      category: 'electronics',
      created_at: '2026-05-26T10:30:00+00:00',
      verdict_short: 'Sharper camera on iPhone.',
    },
    {
      id: 'dddddddd-2222-3333-4444-555555555555',
      product_names: ['CeraVe Cleanser', 'La Roche-Posay Toleriane'],
      schema_version: 2,
      category: 'skincare',
      created_at: '2026-05-25T16:45:00+00:00',
      verdict_short: 'CeraVe wins on dryness; LRP for sensitivity.',
    },
  ],
  total: 2,
  has_more: false,
};

export const mockHistoryListEmpty = {
  comparisons: [],
  total: 0,
  has_more: false,
};
