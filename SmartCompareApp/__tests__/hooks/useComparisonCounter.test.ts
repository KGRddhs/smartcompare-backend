/**
 * useComparisonCounter hook tests — M13-14.
 *
 * The compare gate MUST derive from the already-fetched UsageStatus rather
 * than a hardcoded `used < 3`, so that:
 *   - premium tier is never paywalled,
 *   - an earned referral bonus raises the free cap (the referral loop no
 *     longer dead-ends), and
 *   - a MISSING field / offline hydrate degrades to today's behaviour
 *     (`used < 3`) — the safe fallback that derisks the change with no flag.
 *
 * These two directions (field present → tier-aware; field absent → used<3)
 * are the pins the finding calls for.
 */
import { renderHook, waitFor } from '@testing-library/react-native';
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
    remaining: { daily: 3, monthly: 10 },
    ...overrides,
  } as UsageStatus;
}

beforeEach(async () => {
  jest.clearAllMocks();
  await AsyncStorage.clear();
});

describe('useComparisonCounter — M13-14 tier-aware gate (field PRESENT)', () => {
  it('free tier: at the lifetime-free cap with no bonus → blocked (used < 3)', async () => {
    mockedGetUsageStatus.mockResolvedValue(
      makeStatus({ used: { daily: 0, monthly: 0, lifetime: 3 } })
    );
    const { result } = renderHook(() => useComparisonCounter());
    await waitFor(() => expect(result.current.used).toBe(3));
    expect(result.current.canCompare).toBe(false);
    expect(result.current.shouldShowPaywall).toBe(true);
    // Pill denominator stays the BASE cap; bonus is shown separately.
    expect(result.current.total).toBe(3);
  });

  it('free tier: a referral bonus raises the cap (used 5 < 3+5) → allowed', async () => {
    mockedGetUsageStatus.mockResolvedValue(
      makeStatus({
        used: { daily: 0, monthly: 0, lifetime: 5 },
        limits: { daily: 3, monthly: 15, lifetime_free: 3, monthly_bonus: 5 },
      })
    );
    const { result } = renderHook(() => useComparisonCounter());
    await waitFor(() => expect(result.current.used).toBe(5));
    // 5 < (3 + 5) → still allowed: the referral loop no longer dead-ends.
    expect(result.current.canCompare).toBe(true);
    expect(result.current.shouldShowPaywall).toBe(false);
    // Bonus is NOT folded into `total` (the pill renders it as "+N").
    expect(result.current.total).toBe(3);
  });

  it('free tier: beyond base+bonus → blocked (used 8, cap 3+3)', async () => {
    mockedGetUsageStatus.mockResolvedValue(
      makeStatus({
        used: { daily: 0, monthly: 0, lifetime: 8 },
        limits: { daily: 3, monthly: 13, lifetime_free: 3, monthly_bonus: 3 },
      })
    );
    const { result } = renderHook(() => useComparisonCounter());
    await waitFor(() => expect(result.current.used).toBe(8));
    expect(result.current.canCompare).toBe(false);
  });

  it('premium tier is never paywalled, even well past any free cap', async () => {
    mockedGetUsageStatus.mockResolvedValue(
      makeStatus({
        tier: 'premium',
        used: { daily: 0, monthly: 0, lifetime: 100 },
        limits: { daily: 10, monthly: 70, lifetime_free: 0, monthly_bonus: 0 },
      })
    );
    const { result } = renderHook(() => useComparisonCounter());
    await waitFor(() => expect(result.current.used).toBe(100));
    expect(result.current.canCompare).toBe(true);
    expect(result.current.shouldShowPaywall).toBe(false);
    // Premium keeps the historical denominator, never a "0/0" pill.
    expect(result.current.total).toBe(3);
  });

  it('status present but monthly_bonus absent → bonus defaults to 0', async () => {
    mockedGetUsageStatus.mockResolvedValue(
      makeStatus({
        used: { daily: 0, monthly: 0, lifetime: 2 },
        // No monthly_bonus field — degrade to +0.
        limits: { daily: 3, monthly: 10, lifetime_free: 3 } as any,
      })
    );
    const { result } = renderHook(() => useComparisonCounter());
    await waitFor(() => expect(result.current.used).toBe(2));
    expect(result.current.canCompare).toBe(true); // 2 < 3
  });
});

describe('useComparisonCounter — M13-14 degrade path (field ABSENT / offline)', () => {
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
    // No cached value → used stays 0; canCompare true from the outset.
    await waitFor(() => expect(mockedGetUsageStatus).toHaveBeenCalled());
    expect(result.current.used).toBe(0);
    expect(result.current.canCompare).toBe(true);
    expect(result.current.total).toBe(3);
  });
});
