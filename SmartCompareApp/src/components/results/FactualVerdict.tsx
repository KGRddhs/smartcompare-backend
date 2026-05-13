/**
 * FactualVerdict — Bundle E Phase 3 Task 3.4.
 *
 * Design: docs/plans/2026-05-13-results-quality-overhaul-design.md § Decision 5.
 *
 * Passive renderer of two backend-supplied lines:
 *   line1 — factual delta_text concatenation (e.g. "BHD 30 less, 0.2★ higher").
 *   line2 — conditional alternative for runner-up ("If you want X, the Y fits.").
 *
 * The component does NOT compose its own copy. It MUST fail loud if the
 * backend ever sends evaluative vocabulary — that's defense-in-depth
 * against a regression in build_factual_verdict (backend Task 1.4) before
 * users see a legal-risk claim.
 */

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

import { colors, spacing, typography } from '../../theme';

// Single source of truth for banned vocabulary — mirrors
// app/models/scoring_v2.py::BANNED_DELTA_WORDS.
const BANNED_WORDS = [
  'best',
  'pick',
  'excellent',
  'great',
  'recommend',
  'winner',
  'worst',
  'better',
  'worse',
  'beats',
  'smart',
  'good',
  'choose',
] as const;

const BANNED_PATTERN = new RegExp(`\\b(${BANNED_WORDS.join('|')})\\b`, 'i');

export interface FactualVerdictProps {
  line1: string;
  line2: string;
  testID?: string;
}

export function FactualVerdict({ line1, line2, testID = 'factual-verdict' }: FactualVerdictProps) {
  const violation =
    BANNED_PATTERN.test(line1) || BANNED_PATTERN.test(line2);

  if (violation) {
    return <View testID={`${testID}-contract-violation`} style={styles.violation} />;
  }

  return (
    <View style={styles.container} testID={testID}>
      <Text style={styles.line1}>{line1}</Text>
      {line2 ? <Text style={styles.line2}>{line2}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    gap: spacing.xs,
  },
  line1: {
    ...typography.body,
    color: colors.text.primary,
    fontWeight: '500',
  },
  line2: {
    ...typography.body,
    color: colors.text.secondary,
    fontStyle: 'italic',
  },
  violation: {
    // Zero-sized invisible node. Test queries by testID — the layout itself
    // never paints, but the contract-violation testID is present so
    // FactualVerdict.test.tsx's `queryByTestId('verdict-contract-violation')`
    // resolves and the render-time guard is observable.
    width: 0,
    height: 0,
  },
});

export default FactualVerdict;
