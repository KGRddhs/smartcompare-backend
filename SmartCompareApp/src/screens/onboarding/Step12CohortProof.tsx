/**
 * Step12CohortProof — Phase 2 Task 19 + Phase 5 polish.
 *
 * "388 GCC shoppers helped train this." Hero illustration #2 + 3 bullet
 * stats. Sunk-cost + trust + "I'm not alone." First moment in the flow
 * where the cohort moat earns its visibility per design § 6.
 *
 * Phase 5 polish: 3 bullets stagger-fade-in 80ms each per design § 1
 * "Card slide-in: Stagger 80ms, slide 24px from below + fade". Same
 * choreography pattern reused on Step 15 reveal stat cards.
 */

import React, { useEffect } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withDelay,
  withTiming,
  Easing,
} from 'react-native-reanimated';
import { useTranslation } from 'react-i18next';
import { Button } from '../../components/Button';
import { CohortBarChart } from '../../components/illustrations/CohortBarChart';
import { colors, spacing, typography } from '../../theme';

interface Props {
  onNext: () => void;
  totalShoppers?: number;
  userCohortSize?: number;
}

const STAGGER_MS = 80;
const SLIDE_PX = 24;
const FADE_MS = 320;
// Bullets begin entering AFTER the chart's bar/dot intro (~1.0s) so they
// land as a sequenced reveal rather than a simultaneous overlay.
const BULLET_START_DELAY_MS = 1000;

function StaggeredBullet({
  text,
  delayMs,
  testID,
}: {
  text: string;
  delayMs: number;
  testID: string;
}) {
  const opacity = useSharedValue(0);
  const translateY = useSharedValue(SLIDE_PX);

  useEffect(() => {
    opacity.value = withDelay(
      delayMs,
      withTiming(1, { duration: FADE_MS, easing: Easing.out(Easing.cubic) }),
    );
    translateY.value = withDelay(
      delayMs,
      withTiming(0, { duration: FADE_MS, easing: Easing.out(Easing.cubic) }),
    );
  }, [opacity, translateY, delayMs]);

  const animatedStyle = useAnimatedStyle(() => ({
    opacity: opacity.value,
    transform: [{ translateY: translateY.value }],
  }));

  return (
    <Animated.Text style={[styles.bullet, animatedStyle]} testID={testID}>
      {text}
    </Animated.Text>
  );
}

export function Step12CohortProof({
  onNext,
  totalShoppers = 388,
  userCohortSize = 12,
}: Props) {
  const { t } = useTranslation();

  return (
    <View style={styles.container}>
      <View style={styles.heroBlock}>
        <CohortBarChart
          total={totalShoppers}
          userCohortSize={userCohortSize}
          testID="s12-bar-chart"
        />

        <Text style={styles.title}>{t('onboarding.s12.title')}</Text>

        <View style={styles.bullets}>
          <StaggeredBullet
            text={t('onboarding.s12.bullet_1')}
            delayMs={BULLET_START_DELAY_MS}
            testID="s12-bullet-0"
          />
          <StaggeredBullet
            text={t('onboarding.s12.bullet_2')}
            delayMs={BULLET_START_DELAY_MS + STAGGER_MS}
            testID="s12-bullet-1"
          />
          <StaggeredBullet
            text={t('onboarding.s12.bullet_3')}
            delayMs={BULLET_START_DELAY_MS + STAGGER_MS * 2}
            testID="s12-bullet-2"
          />
        </View>
      </View>

      <View style={styles.footer}>
        <Button
          title={t('onboarding.s12.continue')}
          variant="primary"
          onPress={onNext}
          testID="s12-continue"
        />
      </View>
    </View>
  );
}

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
    paddingTop: spacing.lg,
  },
  title: {
    ...typography.display,
    color: colors.text.primary,
    textAlign: 'center',
    marginTop: spacing.lg,
    marginBottom: spacing.lg,
    paddingHorizontal: spacing.lg,
  },
  bullets: {
    gap: spacing.md,
    paddingHorizontal: spacing.md,
    marginTop: spacing.md,
    alignItems: 'center',
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
