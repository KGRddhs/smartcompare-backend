/**
 * Step01Welcome — Phase 2 Task 13.
 *
 * Big black Q-logo, hero "Look closer. Decide smarter.", Continue,
 * and a small "Already have an account? Sign in" link below per design
 * spec § 2 row 1. The brand confidence carries trust before we ask
 * anything.
 */

import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { useTranslation } from 'react-i18next';
import { Button } from '../../components/Button';
import { QaranIcon } from '../../icons';
import { colors, spacing, typography } from '../../theme';

interface Props {
  onNext: () => void;
  onSignIn?: () => void;
}

export function Step01Welcome({ onNext, onSignIn }: Props) {
  const { t } = useTranslation();

  return (
    <View style={styles.container}>
      <View style={styles.heroBlock}>
        <View style={styles.logoBadge} testID="welcome-qicon">
          <QaranIcon size={56} color={colors.text.onInverse} />
        </View>
        <Text style={styles.title}>{t('onboarding.s1.title')}</Text>
        <Text style={styles.subtitle}>{t('onboarding.s1.subtitle')}</Text>
      </View>

      <View style={styles.footer}>
        <Button
          title={t('onboarding.s1.continue')}
          variant="primary"
          onPress={onNext}
          testID="welcome-continue"
        />
        {onSignIn ? (
          <TouchableOpacity
            onPress={onSignIn}
            accessibilityRole="link"
            style={styles.signInWrap}
            testID="welcome-sign-in-link"
          >
            <Text style={styles.signInText}>
              {t('onboarding.s1.sign_in_link')}
            </Text>
          </TouchableOpacity>
        ) : null}
      </View>
    </View>
  );
}

const LOGO_SIZE = 96;

const styles = StyleSheet.create({
  container: {
    flex: 1,
    paddingHorizontal: spacing.xl,
    paddingVertical: spacing.xl,
    justifyContent: 'space-between',
  },
  heroBlock: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingTop: spacing['3xl'],
  },
  logoBadge: {
    width: LOGO_SIZE,
    height: LOGO_SIZE,
    borderRadius: 24,
    backgroundColor: colors.bg.inverse,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing['2xl'],
  },
  title: {
    ...typography.hero,
    color: colors.text.primary,
    textAlign: 'center',
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
  signInWrap: {
    marginTop: spacing.lg,
    alignItems: 'center',
    paddingVertical: spacing.sm,
  },
  signInText: {
    ...typography.body,
    color: colors.text.secondary,
  },
});
