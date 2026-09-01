/**
 * useComparisonCounter hook tests — M13-14 + M18 CD-interactions-04.
 *
 * CD-interactions-04 (CONFIRMED): the M13-14 gate compared the WRONG AXES —
 * `used < lifetimeFree + bonusRemaining`, where `used` is the backend's
 * NEVER-RESETTING lifetime counter and `bonusRemaining` a MONTHLY-expiring
 * referral bonus. Consequences pinned here:
 *   1. a free user past lifetime-3 was client-paywalled even when the backend
 *      gate (check_usage_allowed: daily 3 / monthly 10+bonus) would allow, and
 *   2. every consumed bonus permanently eroded all FUTURE bonus windows
 *      (lifetime 8 makes a fresh +5 grant compute 8 < 3+5 = false forever).
 *
 * The gate now derives from the SAME axes the backend enforces, all served by
 * GET /usage/status (usage_service.get_usage_status → `remaining`):
 *   canCompare = premium
 *     || remaining.lifetime_free > 0                       (lifetime-free path)
 *     || (remaining.daily > 0 && remaining.monthly > 0)    (recurring path)
 * minus any compares consumed locally since hydration (increment()).
 *
 * Degrade directions retained from M13-14 (the no-flag derisking):
 *   - status null / fetch rejected (offline)      → used < 3 fallback
 *   - status present but `remaining` axes absent  → used < 3 fallback
 * Neither degrade path is ever MORE permissive than the historical gate.
 */
import { act, renderHook, waitFor } from '@testing-library/react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useComparisonCounter } from '../../src/hooks/useComparisonCounter';
import { getUsageStatus, UsageStatus } from '../../src/services/usageService';

jest.mock('../../src/services/usageService', () => ({
  getUsageStatus: jest.fn(),
}));

const mockedGetUsageStatus = getUsageStatus as jest.MockedFunction<
  typeof getUsageStatus
>;
const COUNTER_KEY = '@qaren_free_comparisons_used';

function makeStatus(overrides: Partial<UsageStatus> = {}): UsageStatus {
  return {
    tier: 'free',
    used: { daily: 0, monthly: 0, lifetime: 0 },
    limits: { daily: 3, monthly: 10, lifetime_free: 3, monthly_bonus: 0 },
    remaining: { daily: 3, monthly: 10, lifetime_free: 3 },
    ...overrides,
  } as UsageStatus;
}

beforeEach(async () => {
  jest.clearAllMocks();
  await AsyncStorage.clear();
});

describe('useComparisonCounter — CD-interactions-04 backend-axis gate (fields PRESENT)', () => {
  it('post-lifetime free user with recurring allowance left → ALLOWED (backend would allow)', async () => {
    // The exact case the M13-14 formula got wrong: lifetime 8 >= 3, but the
    // backend gate checks daily/monthly for post-lifetime users and passes.
    mockedGetUsageStatus.mockResolvedValue(
      makeStatus({
        used: { daily: 0, monthly: 0, lifetime: 8 },
        remaining: { daily: 3, monthly: 10, lifetime_free: 0 },
      })
    );
    const { result } = renderHook(() => useComparisonCounter());
    await waitFor(() => expect(result.current.used).toBe(8));
    expect(result.current.canCompare).toBe(true);
    expect(result.current.shouldShowPaywall).toBe(false);
  });

  it('bonus-erosion worked example: lifetime 8 after a consumed +5 window, FRESH +5 grant → ALLOWED', async () => {
    // Old formula: 8 < 3 + 5 = false → permanently paywalled, referral loop
    // dead after one window. Backend: monthly_cap 10+5, monthly_used 0 → allow.
    mockedGetUsageStatus.mockResolvedValue(
      makeStatus({
        used: { daily: 0, monthly: 0, lifetime: 8 },
        limits: { daily: 3, monthly: 15, lifetime_free: 3, monthly_bonus: 5 },
        remaining: { daily: 3, monthly: 15, lifetime_free: 0 },
      })
    );
    const { result } = renderHook(() => useComparisonCounter());
    await waitFor(() => expect(result.current.used).toBe(8));
    expect(result.current.canCompare).toBe(true);
    expect(result.current.shouldShowPaywall).toBe(false);
  });

  it('daily allowance exhausted → BLOCKED even though old formula would allow (3 < 3+5)', async () => {
    mockedGetUsageStatus.mockResolvedValue(
      makeStatus({
        used: { daily: 3, monthly: 3, lifetime: 3 },
        limits: { daily: 3, monthly: 15, lifetime_free: 3, monthly_bonus: 5 },
        remaining: { daily: 0, monthly: 12, lifetime_free: 0 },
      })
    );
    const { result } = renderHook(() => useComparisonCounter());
    await waitFor(() => expect(result.current.used).toBe(3));
    expect(result.current.canCompare).toBe(false);
    expect(result.current.shouldShowPaywall).toBe(true);
  });

  it('monthly allowance exhausted → BLOCKED', async () => {
    mockedGetUsageStatus.mockResolvedValue(
      makeStatus({
        used: { daily: 1, monthly: 10, lifetime: 13 },
        remaining: { daily: 2, monthly: 0, lifetime_free: 0 },
      })
    );
    const { result } = renderHook(() => useComparisonCounter());
    await waitFor(() => expect(result.current.used).toBe(13));
    expect(result.current.canCompare).toBe(false);
    expect(result.current.shouldShowPaywall).toBe(true);
  });

  it('lifetime-free path: remaining.lifetime_free > 0 → ALLOWED, pill total = base cap', async () => {
    mockedGetUsageStatus.mockResolvedValue(
      makeStatus({
        used: { daily: 0, monthly: 0, lifetime: 1 },
        remaining: { daily: 3, monthly: 10, lifetime_free: 2 },
      })
    );
    const { result } = renderHook(() => useComparisonCounter());
    await waitFor(() => expect(result.current.used).toBe(1));
    expect(result.current.canCompare).toBe(true);
    // Pill denominator stays the BASE lifetime-free cap.
    expect(result.current.total).toBe(3);
  });

  it('premium tier is never client-paywalled (backend 429 is the backstop)', async () => {
    mockedGetUsageStatus.mockResolvedValue(
      makeStatus({
        tier: 'premium',
        used: { daily: 0, monthly: 0, lifetime: 100 },
        limits: { daily: 10, monthly: 70, lifetime_free: 0, monthly_bonus: 0 },
        remaining: { daily: 10, monthly: 70, lifetime_free: 0 },
      })
    );
    const { result } = renderHook(() => useComparisonCounter());
    await waitFor(() => expect(result.current.used).toBe(100));
    expect(result.current.canCompare).toBe(true);
    expect(result.current.shouldShowPaywall).toBe(false);
    // Premium keeps the historical denominator, never a "0/0" pill.
    expect(result.current.total).toBe(3);
  });

  it('compares consumed locally since hydration count against the remaining axes', async () => {
    // Hydrate with exactly 1 daily compare left. The old formula blocked this
    // user at mount (5 >= 3); the backend allows exactly one more.
    mockedGetUsageStatus.mockResolvedValue(
      makeStatus({
        used: { daily: 2, monthly: 5, lifetime: 5 },
        remaining: { daily: 1, monthly: 5, lifetime_free: 0 },
      })
    );
    const { result } = renderHook(() => useComparisonCounter());
    await waitFor(() => expect(result.current.used).toBe(5));
    expect(result.current.canCompare).toBe(true);

    await act(async () => {
      await result.current.increment();
    });
    // used 6, one compare consumed locally → effective remaining.daily 0.
    expect(result.current.used).toBe(6);
    expect(result.current.canCompare).toBe(false);
    expect(result.current.shouldShowPaywall).toBe(true);
  });
});

describe('useComparisonCounter — degrade paths (offline / older backend)', () => {
  it('offline (status null), cached used=1 → allowed via used < 3', async () => {
    mockedGetUsageStatus.mockResolvedValue(null);
    await AsyncStorage.setItem(COUNTER_KEY, '1');
    const { result } = renderHook(() => useComparisonCounter());
    await waitFor(() => expect(result.current.used).toBe(1));
    expect(result.current.canCompare).toBe(true);
    expect(result.current.total).toBe(3);
  });

  it('offline (status null), cached used=5 → blocked via used < 3', async () => {
    mockedGetUsageStatus.mockResolvedValue(null);
    await AsyncStorage.setItem(COUNTER_KEY, '5');
    const { result } = renderHook(() => useComparisonCounter());
    await waitFor(() => expect(result.current.used).toBe(5));
    expect(result.current.canCompare).toBe(false);
    expect(result.current.shouldShowPaywall).toBe(true);
  });

  it('fetch rejects (offline), no cache → used 0, allowed (used < 3)', async () => {
    mockedGetUsageStatus.mockRejectedValue(new Error('offline'));
    const { result } = renderHook(() => useComparisonCounter());
    await waitFor(() => expect(mockedGetUsageStatus).toHaveBeenCalled());
    expect(result.current.used).toBe(0);
    expect(result.current.canCompare).toBe(true);
    expect(result.current.total).toBe(3);
  });

  it('older backend: `remaining` axes ABSENT → used < 3 fallback (used 2 → allowed)', async () => {
    mockedGetUsageStatus.mockResolvedValue(
      makeStatus({
        used: { daily: 0, monthly: 0, lifetime: 2 },
        remaining: undefined as any,
      })
    );
    const { result } = renderHook(() => useComparisonCounter());
    await waitFor(() => expect(result.current.used).toBe(2));
    expect(result.current.canCompare).toBe(true);
  });

  it('older backend: `remaining` axes ABSENT → used < 3 fallback (used 5 → blocked, never MORE permissive)', async () => {
    mockedGetUsageStatus.mockResolvedValue(
      makeStatus({
        used: { daily: 0, monthly: 0, lifetime: 5 },
        remaining: undefined as any,
      })
    );
    const { result } = renderHook(() => useComparisonCounter());
    await waitFor(() => expect(result.current.used).toBe(5));
    expect(result.current.canCompare).toBe(false);
    expect(result.current.shouldShowPaywall).toBe(true);
  });
});
