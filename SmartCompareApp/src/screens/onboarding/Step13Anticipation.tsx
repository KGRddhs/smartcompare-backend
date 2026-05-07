/**
 * Step13Anticipation — Phase 2 Task 20.
 *
 * Build-up before the theatrical loading payoff on screen 14. Renders
 * ConcentricMotif illustration #3 + "Time to build your shopping advisor"
 * + "Build my advisor" CTA. See design spec § 2 row 13.
 */

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useTranslation } from 'react-i18next';
import { Button } from '../../components/Button';
import { ConcentricMotif } from '../../components/illustrations/ConcentricMotif';
import { colors, spacing, typography } from '../../theme';

interface Props {
  onNext: () => void;
}

export function Step13Anticipation({ onNext }: Props) {
  const { t } = useTranslation();

  return (
    <View style={styles.container}>
      <View style={styles.heroBlock}>
        <ConcentricMotif size={240} testID="s13-concentric" />
        <Text style={styles.title}>{t('onboarding.s13.title')}</Text>
        <Text style={styles.subtitle}>{t('onboarding.s13.subtitle')}</Text>
      </View>

      <View style={styles.footer}>
        <Button
          title={t('onboarding.s13.cta')}
          variant="primary"
          onPress={onNext}
          testID="s13-cta"
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
    justifyContent: 'center',
  },
  title: {
    ...typography.display,
    color: colors.text.primary,
    textAlign: 'center',
    marginTop: spacing.xl,
    marginBottom: spacing.md,
    paddingHorizontal: spacing.lg,
  },
  subtitle: {
    ...typography.body,
    color: colors.text.secondary,
    textAlign: 'center',
    paddingHorizontal: spacing.lg,
  },
  footer: {
    paddingTop: spacing.lg,
  },
});
