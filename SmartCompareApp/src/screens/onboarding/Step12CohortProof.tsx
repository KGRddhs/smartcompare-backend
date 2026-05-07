/**
 * Step12CohortProof — Phase 2 Task 19.
 *
 * "388 GCC shoppers helped train this." Hero illustration #2 + 3 bullet
 * stats. Sunk-cost + trust + "I'm not alone." First moment in the flow
 * where the cohort moat earns its visibility per design § 6.
 *
 * Bullet stagger animation deferred to Phase 5 polish — for now the 3
 * bullets render in their final state (the chart itself animates).
 */

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useTranslation } from 'react-i18next';
import { Button } from '../../components/Button';
import { CohortBarChart } from '../../components/illustrations/CohortBarChart';
import { colors, spacing, typography } from '../../theme';

interface Props {
  onNext: () => void;
  totalShoppers?: number;
  userCohortSize?: number;
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
          <Text style={styles.bullet}>{t('onboarding.s12.bullet_1')}</Text>
          <Text style={styles.bullet}>{t('onboarding.s12.bullet_2')}</Text>
          <Text style={styles.bullet}>{t('onboarding.s12.bullet_3')}</Text>
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
