import { useState, useEffect, useCallback } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';

const COUNTER_KEY = '@qaren_free_comparisons_used';
const FREE_LIMIT = 3;

export function useComparisonCounter() {
  const [used, setUsed] = useState(0);

  useEffect(() => {
    AsyncStorage.getItem(COUNTER_KEY).then((val) => {
      if (val) setUsed(parseInt(val, 10));
    });
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
