/**
 * Step15Reveal — Phase 2 Task 22.
 *
 * "Your shopping advisor is ready" — the payoff the loading earned.
 * RevealBurst illustration #5 + 4 stat cards in 2x2 grid + black CTA.
 * See design spec § 2 row 15.
 *
 * Stat-card stagger animation deferred to Phase 5 polish — cards render
 * in their final state for now (the burst illustration carries the
 * theatrical moment).
 */

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
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
          <StatCard
            testID="stat-match-quality"
            label={t('onboarding.s15.match_quality')}
            value={profile.matchQuality}
          />
          <StatCard
            testID="stat-top-priority"
            label={t('onboarding.s15.top_priority')}
            value={profile.topPriority}
          />
        </View>
        <View style={styles.gridRow}>
          <StatCard
            testID="stat-budget-tier"
            label={t('onboarding.s15.budget_tier')}
            value={profile.budgetTier}
          />
          <View testID="stat-peer-count" style={[styles.card]}>
            <Text style={styles.cardLabel}>{t('onboarding.s15.peer_count')}</Text>
            <CounterTicker
              target={profile.peerCount}
              duration={1200}
              style={styles.cardValue}
            />
          </View>
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
  card: {
    flex: 1,
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
