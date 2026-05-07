/**
 * Step15Reveal — Phase 2 Task 22 + Phase 5 polish.
 *
 * "Your shopping advisor is ready" — the payoff the loading earned.
 * RevealBurst illustration #5 + 4 stat cards in 2x2 grid + black CTA.
 * See design spec § 2 row 15.
 *
 * Phase 5 polish: 4 stat cards stagger-fade-in 80ms each per design § 1
 * "Card slide-in: Stagger 80ms, slide 24px from below + fade". Same
 * choreography pattern as Step12 bullets — landed via shared
 * StaggeredReveal helper inline.
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
import { RevealBurst } from '../../components/illustrations/RevealBurst';
import { CounterTicker } from '../../components/CounterTicker';
import { colors, spacing, typography, radii } from '../../theme';

export interface RevealProfile {
  matchQuality: string;
  topPriority: string;
  budgetTier: string;
  peerCount: number;
}

interface Props {
  onNext: () => void;
  profile: RevealProfile;
}

const STAGGER_MS = 80;
const SLIDE_PX = 24;
const FADE_MS = 320;
// Cards begin entering AFTER the burst illustration's intro
// (~600ms — burst lines extend 320ms + check stroke-draw at 500ms +
// some margin) so the reveal sequence reads as theatrical rather
// than simultaneous overlay.
const CARDS_START_DELAY_MS = 600;

function StaggeredCardWrap({
  children,
  delayMs,
  testID,
  style,
}: {
  children: React.ReactNode;
  delayMs: number;
  testID: string;
  style?: any;
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
    <Animated.View
      testID={testID}
      style={[styles.cardWrap, style, animatedStyle]}
    >
      {children}
    </Animated.View>
  );
}

export function Step15Reveal({ onNext, profile }: Props) {
  const { t } = useTranslation();

  return (
    <View style={styles.container}>
      <View style={styles.heroBlock}>
        <RevealBurst size={200} testID="s15-burst" />
        <Text style={styles.title}>{t('onboarding.s15.title')}</Text>
      </View>

      <View style={styles.grid}>
        <View style={styles.gridRow}>
          <StaggeredCardWrap
            delayMs={CARDS_START_DELAY_MS + STAGGER_MS * 0}
            testID="stat-card-wrap-0"
          >
            <StatCard
              testID="stat-match-quality"
              label={t('onboarding.s15.match_quality')}
              value={profile.matchQuality}
            />
          </StaggeredCardWrap>
          <StaggeredCardWrap
            delayMs={CARDS_START_DELAY_MS + STAGGER_MS * 1}
            testID="stat-card-wrap-1"
          >
            <StatCard
              testID="stat-top-priority"
              label={t('onboarding.s15.top_priority')}
              value={profile.topPriority}
            />
          </StaggeredCardWrap>
        </View>
        <View style={styles.gridRow}>
          <StaggeredCardWrap
            delayMs={CARDS_START_DELAY_MS + STAGGER_MS * 2}
            testID="stat-card-wrap-2"
          >
            <StatCard
              testID="stat-budget-tier"
              label={t('onboarding.s15.budget_tier')}
              value={profile.budgetTier}
            />
          </StaggeredCardWrap>
          <StaggeredCardWrap
            delayMs={CARDS_START_DELAY_MS + STAGGER_MS * 3}
            testID="stat-card-wrap-3"
          >
            <View testID="stat-peer-count" style={[styles.card]}>
              <Text style={styles.cardLabel}>{t('onboarding.s15.peer_count')}</Text>
              <CounterTicker
                target={profile.peerCount}
                duration={1200}
                style={styles.cardValue}
              />
            </View>
          </StaggeredCardWrap>
        </View>
      </View>

      <View style={styles.footer}>
        <Button
          title={t('onboarding.s15.cta')}
          variant="primary"
          onPress={onNext}
          testID="s15-cta"
        />
      </View>
    </View>
  );
}

interface StatCardProps {
  testID: string;
  label: string;
  value: string;
}

function StatCard({ testID, label, value }: StatCardProps) {
  return (
    <View testID={testID} style={styles.card}>
      <Text style={styles.cardLabel}>{label}</Text>
      <Text style={styles.cardValue}>{value}</Text>
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
    alignItems: 'center',
    paddingTop: spacing.lg,
  },
  title: {
    ...typography.display,
    color: colors.text.primary,
    textAlign: 'center',
    marginTop: spacing.lg,
    paddingHorizontal: spacing.lg,
  },
  grid: {
    gap: spacing.md,
    marginVertical: spacing.lg,
  },
  gridRow: {
    flexDirection: 'row',
    gap: spacing.md,
  },
  cardWrap: {
    flex: 1,
  },
  card: {
    backgroundColor: colors.bg.secondary,
    borderRadius: radii.card,
    padding: spacing.lg,
  },
  cardLabel: {
    ...typography.caption,
    color: colors.text.secondary,
    marginBottom: spacing.xs,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  cardValue: {
    ...typography.title,
    color: colors.text.primary,
  },
  footer: {
    paddingTop: spacing.lg,
  },
});
