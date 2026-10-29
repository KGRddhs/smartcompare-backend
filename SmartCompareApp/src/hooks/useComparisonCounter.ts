import { useState, useEffect, useCallback } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { getUsageStatus, UsageStatus } from '../services/usageService';
import { isDailyScope } from '../utils/resetTime';

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
        const lifetime = fetched?.used?.lifetime;
        if (fetched && typeof lifetime === 'number') {
          if (!cancelled) {
            setStatus(fetched);
            setUsed(lifetime);
            AsyncStorage.setItem(COUNTER_KEY, String(lifetime));
          }
          return;
        }
        // S81-08 (RULINGS_S81_08 R-S08-13): a status without the lifetime
        // counter (S81-09 may retire it) still drives the gate when it carries
        // the daily and monthly axes; `used` then keeps the local cache below.
        if (
          fetched &&
          typeof fetched.remaining?.daily === 'number' &&
          typeof fetched.remaining?.monthly === 'number' &&
          !cancelled
        ) {
          setStatus(fetched);
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

  // S81-08 (R-S08-2 / GATE GC-5): the reset time reaches the pill only when the
  // server names a DAILY counted axis. The count beside it is then that axis
  // (below, RULINGS_FIX1_S81_08 F1-8) and HomeScreen renders the resets node
  // right after the count, before the monthly bonus (F1-9). Null otherwise.
  const statusResetsAt = status?.resets_at;
  const resetsAt =
    typeof statusResetsAt === 'string' && isDailyScope(status?.counted_scope) ? statusResetsAt : null;

  // RULINGS_FIX1_S81_08 F1-8 (the S81-09 contract, its brief Q8): a status
  // whose counted_scope names a daily axis ('daily' / 'device_daily') and that
  // carries THAT axis's remaining drives the pill: `total` = the daily cap,
  // `used` = total minus the axis's remaining (less the compares consumed here
  // since hydration), never lifetime_free - used.lifetime. A status without a
  // named daily axis (build-3 backends) keeps the lifetime math above.
  const countedScope = status?.counted_scope;
  const axisRemaining =
    countedScope === 'daily' || countedScope === 'device_daily' ? remaining?.[countedScope] : undefined;
  let pillUsed = used;
  let pillTotal = total;
  if (typeof axisRemaining === 'number') {
    const dailyCap = status?.limits?.daily;
    pillTotal = typeof dailyCap === 'number' ? dailyCap : FREE_LIMIT;
    pillUsed = Math.max(0, pillTotal - Math.max(0, axisRemaining - sessionConsumed));
  }

  return { used: pillUsed, total: pillTotal, canCompare, shouldShowPaywall, increment, resetsAt };
}
