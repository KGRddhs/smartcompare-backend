/**
 * Step05Trust — Phase 2 Task 14 + Phase 5 polish.
 *
 * Trust bridge — pure typography + small filled lock icon, hero "Your
 * data stays yours. We just compare." + 3 thin bullets.
 *
 * Per design § 2 row 5 + Cal-AI weight notes: the lock badge mounts with
 * a subtle 5° rotation (filled, geometric, chunky). Reanimated drives
 * the rotate transform via useAnimatedStyle so reduced-motion settings
 * collapse it gracefully on the host platform; under jest the mock
 * returns the target value verbatim so the test suite can assert it.
 *
 * Pre-empts the "why do you need this?" objection BEFORE we ask for age,
 * gender, etc. Copy strictly follows § 4g audit ("Your data lives on your
 * device", "We match anonymously — no name attached", "Skip anything —
 * and edit later").
 */

import React, { useEffect } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withTiming,
  Easing,
} from 'react-native-reanimated';
import { useTranslation } from 'react-i18next';
import { Button } from '../../components/Button';
import { colors, spacing, typography, radii } from '../../theme';

interface Props {
  onNext: () => void;
}

const ROTATE_DEG_TARGET = 5;
const ROTATE_DURATION_MS = 320;

export function Step05Trust({ onNext }: Props) {
  const { t } = useTranslation();
  const rotation = useSharedValue(0);

  useEffect(() => {
    rotation.value = withTiming(ROTATE_DEG_TARGET, {
      duration: ROTATE_DURATION_MS,
      easing: Easing.out(Easing.cubic),
    });
  }, [rotation]);

  const lockAnimatedStyle = useAnimatedStyle(() => ({
    transform: [{ rotate: `${rotation.value}deg` }],
  }));

  return (
    <View style={styles.container}>
      <View style={styles.heroBlock}>
        <Animated.View
          style={[styles.lockBadge, lockAnimatedStyle]}
          testID="trust-lock-icon"
        >
          {/* Geometric lock glyph; full custom icon swap-in lives in the
              broader icon-system rounding-out. The 5° rotation lands the
              Cal-AI "weight" cue per design § 2 row 5. */}
          <Text style={styles.lockGlyph}>{'\u{1F512}'}</Text>
        </Animated.View>

        <Text style={styles.title}>{t('onboarding.s5.title')}</Text>

        <View style={styles.bullets}>
          <Text style={styles.bullet}>{t('onboarding.s5.bullet_1')}</Text>
          <Text style={styles.bullet}>{t('onboarding.s5.bullet_2')}</Text>
          <Text style={styles.bullet}>{t('onboarding.s5.bullet_3')}</Text>
        </View>
      </View>

      <View style={styles.footer}>
        <Button
          title={t('onboarding.s5.continue')}
          variant="primary"
          onPress={onNext}
          testID="trust-continue"
        />
      </View>
    </View>
  );
}

const LOCK_SIZE = 56;

const styles = StyleSheet.create({
  container: {
    flex: 1,
    paddingHorizontal: spacing.xl,
    paddingVertical: spacing.lg,
    justifyContent: 'space-between',
  },
  heroBlock: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: spacing.xl,
  },
  lockBadge: {
    width: LOCK_SIZE,
    height: LOCK_SIZE,
    borderRadius: radii.button,
    backgroundColor: colors.accentLight,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.xl,
  },
  lockGlyph: {
    fontSize: 28,
  },
  title: {
    ...typography.display,
    color: colors.text.primary,
    textAlign: 'center',
    marginBottom: spacing.xl,
    paddingHorizontal: spacing.lg,
  },
  bullets: {
    gap: spacing.md,
    paddingHorizontal: spacing.lg,
    marginTop: spacing.lg,
  },
  bullet: {
    ...typography.body,
    color: colors.text.secondary,
    textAlign: 'center',
  },
  footer: {
    paddingTop: spacing.lg,
  },
});
