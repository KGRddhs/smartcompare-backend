/**
 * ConfidencePills — "UI Kit — Mobile Results" rebuild (Phase 4.2).
 *
 * 3-pill horizontal row under "What we know". Each pill is the unused
 * primitives/ConfidencePill (a COLORED DOT + label), e.g. "● Price · High"
 * (green dot), "● Reviews · Medium" (amber dot), "● Specs · High". The dot
 * is the load-bearing signal; the pill body is a calm bg.secondary chip
 * with a hairline border (mockup ConfidencePill, JSX 84-101). Tap opens the
 * "What we know" bottom sheet (caller-owned modal state via onPillPress).
 *
 * Backend confidence_legs use the strong|acceptable|weak vocabulary; the
 * primitive uses high|medium|low dot colors. Mapping:
 *  - strong     → high   (emerald dot)
 *  - acceptable → medium (amber dot — soft middle ground, never alarmist)
 *  - weak       → low    (muted gray dot — never red, never destructive)
 *
 * Suppression rules:
 *  - When `hidePricePill === true` (caller computes via `anyEstimated()`
 *    helper), the Price pill is omitted entirely (§ 5c — price provenance
 *    is silent in the UI; no "estimated" copy anywhere).
 *  - A leg whose confidence is `undefined` is omitted entirely (no
 *    placeholder pill).
 *  - When no legs are present, the component renders `null` (caller may
 *    decide whether to slot in a fallback).
 */
import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { useTranslation } from 'react-i18next';

import { colors, spacing } from '../../theme';
import { ConfidencePill } from '../primitives/ConfidencePill';

type Level = 'strong' | 'acceptable' | 'weak';
type DotLevel = 'high' | 'medium' | 'low';
type Leg = 'price' | 'reviews' | 'specs';

interface Props {
  confidence: {
    price?: Level;
    reviews?: Level;
    specs?: Level;
  };
  hidePricePill?: boolean;
  onPillPress: (leg: Leg) => void;
  testID?: string;
}

const PILLS: Array<{ leg: Leg; labelKey: string }> = [
  { leg: 'price',   labelKey: 'results.confidence.pill.price' },
  { leg: 'reviews', labelKey: 'results.confidence.pill.reviews' },
  { leg: 'specs',   labelKey: 'results.confidence.pill.specs' },
];

// Backend strong|acceptable|weak → primitive dot level + level-word key.
const LEVEL_MAP: Record<Level, { dot: DotLevel; wordKey: string }> = {
  strong:     { dot: 'high',   wordKey: 'results.confidence.level.high' },
  acceptable: { dot: 'medium', wordKey: 'results.confidence.level.medium' },
  weak:       { dot: 'low',    wordKey: 'results.confidence.level.low' },
};

export function ConfidencePills({ confidence, hidePricePill, onPillPress, testID = 'confidence-pills' }: Props) {
  const { t } = useTranslation();

  const renderable = PILLS.filter((p) => {
    if (p.leg === 'price' && hidePricePill) return false;
    return confidence[p.leg] !== undefined;
  });

  if (renderable.length === 0) return null;

  return (
    <View style={styles.row} testID={testID}>
      {renderable.map((p) => {
        const level = confidence[p.leg]!;
        const { dot, wordKey } = LEVEL_MAP[level];
        // Composed label "Leg · Level". The leg name is a nested <Text> so
        // it stays individually queryable (existing ConfidencePills test
        // does getByText on the leg key); the primitive renders the whole
        // node inside its label <Text>.
        const label = (
          <>
            <Text>{t(p.labelKey)}</Text>
            {' · '}
            {t(wordKey)}
          </>
        );
        return (
          <TouchableOpacity
            key={p.leg}
            testID={`${testID}-${p.leg}`}
            accessibilityRole="button"
            activeOpacity={0.7}
            onPress={() => onPillPress(p.leg)}
          >
            <ConfidencePill
              label={label}
              level={dot}
              dotTestID={`${testID}-${p.leg}-dot`}
            />
          </TouchableOpacity>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    gap: spacing.sm,
    flexWrap: 'wrap',
    paddingVertical: spacing.xs,
  },
});
