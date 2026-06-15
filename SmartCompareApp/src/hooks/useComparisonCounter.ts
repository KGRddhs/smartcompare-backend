import { useState, useEffect, useCallback } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { getUsageStatus } from '../services/usageService';

const COUNTER_KEY = '@qaren_free_comparisons_used';
const FREE_LIMIT = 3;

export function useComparisonCounter() {
  const [used, setUsed] = useState(0);

  // Source of truth = the BACKEND lifetime counter. Previously this hook tracked
  // `used` purely in AsyncStorage, so it never reflected the server: once it hit 3
  // the paywall was stuck forever and admin usage resets never propagated. Now we
  // hydrate from the backend on mount and fall back to the local cache only when
  // the fetch fails (offline).
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const status = await getUsageStatus();
        if (status && typeof status.used?.lifetime === 'number') {
          if (!cancelled) {
            setUsed(status.used.lifetime);
            AsyncStorage.setItem(COUNTER_KEY, String(status.used.lifetime));
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

  const canCompare = used < FREE_LIMIT;
  const shouldShowPaywall = used >= FREE_LIMIT;

  return { used, total: FREE_LIMIT, canCompare, shouldShowPaywall, increment };
}
