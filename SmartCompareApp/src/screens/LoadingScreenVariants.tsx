/**
 * LoadingScreenVariants — Bundle E S2.x (forward placeholder for S0 gate).
 *
 * This file lands its full implementation during S2 (frontend lane plan
 * § S2.x). It exports ConcentricVariant + StreamingCardsVariant. Mode
 * "onboarding" always uses ConcentricVariant (Step14 theatrical 3.2s).
 * Mode "comparison" picks one of the two via useMemo.
 *
 * The current shape is a minimum stub so test scaffolds + tsc can resolve
 * the import. Behavioral assertions in __tests__/LoadingScreen.bundleE.test.tsx
 * are expected to be partially RED until S2; the stub's "no throw" gate
 * keeps the snapshot tests honest.
 */
import React, { useEffect, useMemo } from 'react';
import { View, StyleSheet } from 'react-native';
import { LoadingRings } from '../components/hero/LoadingRings';
import { colors } from '../theme';

interface Props {
  variant?: 'concentric' | 'streaming';
  mode: 'onboarding' | 'comparison';
  /**
   * Comparison mode: when `ready=true`, the loader exits on the next
   * tick (assuming min-display floor satisfied in onboarding mode).
   * Onboarding mode ignores `ready` and always waits the full
   * minDisplayMs before firing onDone — the theatrical floor.
   */
  ready?: boolean;
  onDone?: () => void;
  /** Minimum on-screen duration in onboarding mode (ms). */
  minDisplayMs?: number;
  testID?: string;
}

const ONBOARDING_MIN_DISPLAY_MS = 3200;

export function LoadingScreenVariants({
  variant,
  mode,
  ready: _ready,
  onDone,
  minDisplayMs = ONBOARDING_MIN_DISPLAY_MS,
  testID,
}: Props) {
  // Mode "onboarding" always concentric (Step14). Mode "comparison"
  // resolves the variant on first mount via useMemo so re-renders during
  // load do not flip the variant.
  const resolvedVariant = useMemo<'concentric' | 'streaming'>(() => {
    if (mode === 'onboarding') return 'concentric';
    if (variant) return variant;
    return Math.random() < 0.5 ? 'concentric' : 'streaming';
  }, [mode, variant]);

  useEffect(() => {
    if (mode !== 'onboarding' || !onDone) return;
    const handle = setTimeout(onDone, minDisplayMs);
    return () => clearTimeout(handle);
  }, [mode, onDone, minDisplayMs]);

  return (
    <View style={styles.root} testID={testID}>
      {resolvedVariant === 'concentric' ? (
        <LoadingRings testID="loading-screen-concentric" />
      ) : (
        <View testID="loading-screen-streaming" style={styles.streamingStub} />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.bg.primary,
  },
  streamingStub: {
    width: 280,
    height: 200,
    backgroundColor: colors.bg.secondary,
    borderRadius: 16,
  },
});
