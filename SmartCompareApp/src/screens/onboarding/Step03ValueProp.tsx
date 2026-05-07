/**
 * Step03ValueProp — Phase 2 Task 13.
 *
 * Phone mockup hero illustration #1 + "Stop guessing. Start knowing."
 * + Continue. Show value before asking for any data. See design spec
 * § 2 row 3.
 */

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useTranslation } from 'react-i18next';
import { Button } from '../../components/Button';
import { PhoneMockup } from '../../components/illustrations/PhoneMockup';
import { colors, spacing, typography } from '../../theme';

interface Props {
  onNext: () => void;
}

export function Step03ValueProp({ onNext }: Props) {
  const { t } = useTranslation();

  return (
    <View style={styles.container}>
      <View style={styles.heroBlock}>
        <PhoneMockup size={280} testID="s3-phone-mockup" />
        <Text style={styles.title}>{t('onboarding.s3.title')}</Text>
        <Text style={styles.subtitle}>{t('onboarding.s3.subtitle')}</Text>
      </View>

      <View style={styles.footer}>
        <Button
          title={t('onboarding.s3.continue')}
          variant="primary"
          onPress={onNext}
          testID="s3-continue"
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
