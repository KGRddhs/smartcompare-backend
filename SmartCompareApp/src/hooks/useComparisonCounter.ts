import { useState, useEffect, useCallback } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { getUsageStatus, UsageStatus } from '../services/usageService';

const COUNTER_KEY = '@qaren_free_comparisons_used';
const FREE_LIMIT = 3;

export function useComparisonCounter() {
  const [used, setUsed] = useState(0);
  const [status, setStatus] = useState<UsageStatus | null>(null);

  // Source of truth = the BACKEND lifetime counter. Previously this hook tracked
  // `used` purely in AsyncStorage, so it never reflected the server: once it hit 3
  // the paywall was stuck forever and admin usage resets never propagated. Now we
  // hydrate from the backend on mount and fall back to the local cache only when
  // the fetch fails (offline).
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const fetched = await getUsageStatus();
        if (fetched && typeof fetched.used?.lifetime === 'number') {
          if (!cancelled) {
            setStatus(fetched);
            setUsed(fetched.used.lifetime);
            AsyncStorage.setItem(COUNTER_KEY, String(fetched.used.lifetime));
          }
          return;
        }
      } catch {
        // offline / error → fall back to the local cache below
      }
      const val = await AsyncStorage.getItem(COUNTER_KEY);
      if (!cancelled && val) setUsed(parseInt(val, 10));
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const increment = useCallback(async () => {
    const newCount = used + 1;
    setUsed(newCount);
    await AsyncStorage.setItem(COUNTER_KEY, String(newCount));
    return newCount;
  }, [used]);

  // M18 CD-interactions-04 (supersedes the M13-14 formula): derive the gate from
  // the SAME AXES the backend enforces. The old formula compared the backend's
  // NEVER-RESETTING lifetime counter against a MONTHLY-expiring referral bonus
  // (`used < lifetime_free + monthly_bonus`), so a free user past lifetime-3 was
  // client-paywalled even when check_usage_allowed would pass (daily 3 / monthly
  // 10+bonus), and every consumed bonus permanently eroded all FUTURE bonus
  // windows (lifetime 8 makes a fresh +5 grant compute 8 < 3+5 = false forever).
  //
  // Backend gate (usage_service.check_usage_allowed), mirrored here off the
  // `remaining` block get_usage_status already serves:
  //   free with lifetime-free left → allowed (remaining.lifetime_free > 0)
  //   otherwise                    → allowed iff daily AND monthly remain
  // Compares consumed locally since hydration (increment()) are subtracted from
  // each axis so the gate moves within a session without a refetch; the backend
  // increments all three counters per compare, so one shared delta is faithful.
  //
  // Safe-fallback derisking retained from M13-14 (no flag — RN has no per-call
  // env flag): when `status` is null (offline) or the `remaining` axes are
  // absent (older backend), the gate collapses to the historical `used < 3` —
  // never MORE permissive than the data actually present supports.
  const lifetimeFree = status?.limits?.lifetime_free ?? FREE_LIMIT;
  const isPremium = status?.tier === 'premium';
  const remaining = status?.remaining;
  const hasBackendAxes =
    typeof remaining?.daily === 'number' && typeof remaining?.monthly === 'number';
  const fetchedLifetime = status?.used?.lifetime;
  const sessionConsumed =
    typeof fetchedLifetime === 'number' ? Math.max(0, used - fetchedLifetime) : 0;
  const backendAllows =
    hasBackendAxes &&
    ((remaining.lifetime_free ?? 0) - sessionConsumed > 0 ||
      (remaining.daily - sessionConsumed > 0 &&
        remaining.monthly - sessionConsumed > 0));
  const canCompare =
    isPremium || (hasBackendAxes ? backendAllows : used < FREE_LIMIT);
  const shouldShowPaywall = !canCompare;

  // Pill denominator = the BASE lifetime-free cap only. The header pill renders
  // the referral bonus separately as "+N", so folding the bonus into `total`
  // here would double-count it. Premium keeps the historical FREE_LIMIT so the
  // pill never shows a "0/0" (premium's lifetime_free is 0 by design).
  const total = isPremium ? FREE_LIMIT : lifetimeFree;

  return { used, total, canCompare, shouldShowPaywall, increment };
}
