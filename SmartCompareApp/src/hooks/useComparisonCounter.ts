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

  // M13-14: derive the gate from the already-fetched UsageStatus rather than
  // hardcoding `used < 3`. The backend grants premium unlimited and free users a
  // lifetime-free window plus any active referral bonus, so a hardcoded `used < 3`
  // dead-ends BOTH the base allowance and the entire referral incentive loop at a
  // fixed 3 — every blocked entry point routes to the "Coming soon" paywall.
  //
  // Safe-fallback derisking (no flag needed — RN has no per-call env flag): every
  // field is read defensively so a MISSING field degrades to today's behaviour.
  // When `status` is null (offline hydrate) or the fields are absent (older
  // backend), `tier` is undefined, `lifetimeFree` falls back to FREE_LIMIT and
  // `bonusRemaining` to 0, so `canCompare` collapses to `used < 3` — never MORE
  // permissive than today, only tier-aware when the data is actually present.
  const lifetimeFree = status?.limits?.lifetime_free ?? FREE_LIMIT;
  const bonusRemaining = status?.limits?.monthly_bonus ?? 0;
  const isPremium = status?.tier === 'premium';
  const canCompare = isPremium || used < lifetimeFree + bonusRemaining;
  const shouldShowPaywall = !canCompare;

  // Pill denominator = the BASE lifetime-free cap only. The header pill renders
  // the referral bonus separately as "+N", so folding the bonus into `total`
  // here would double-count it. Premium keeps the historical FREE_LIMIT so the
  // pill never shows a "0/0" (premium's lifetime_free is 0 by design).
  const total = isPremium ? FREE_LIMIT : lifetimeFree;

  return { used, total, canCompare, shouldShowPaywall, increment };
}
