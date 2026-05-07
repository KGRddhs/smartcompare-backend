/**
 * Step16Account — Phase 2 Task 23.
 *
 * "Save your advisor" — Apple / Google / Email. NO skip link per design
 * § 2 row 16. Sunk-cost makes drop-off lowest here, account is required
 * for Loop 2 + cohort persistence + push notifications + Apple guideline
 * 4.8 ("if you offer Sign in with X, you must offer Apple Sign-In").
 *
 * The screen is presentational — it surfaces 3 choice buttons. The
 * orchestrator (Task 24) wires the actual authService.signInWithGoogle
 * / signInWithApple / "navigate to Register" calls and handles success
 * to advance to step 17.
 */

import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Platform } from 'react-native';
import { useTranslation } from 'react-i18next';
import { colors, spacing, typography, radii } from '../../theme';

export type AuthMethod = 'apple' | 'google' | 'email';

interface Props {
  onSelectMethod: (method: AuthMethod) => void;
  /** Whether Apple Sign-In is supported on this platform. iOS only. */
  appleAvailable?: boolean;
}

export function Step16Account({ onSelectMethod, appleAvailable = Platform.OS === 'ios' }: Props) {
  const { t } = useTranslation();

  return (
    <View style={styles.container}>
      <View style={styles.heroBlock}>
        <Text style={styles.title}>{t('onboarding.s16.title')}</Text>
        <Text style={styles.subtitle}>{t('onboarding.s16.subtitle')}</Text>
      </View>

      <View style={styles.choices}>
        {appleAvailable ? (
          <TouchableOpacity
            testID="account-apple"
            onPress={() => onSelectMethod('apple')}
            accessibilityRole="button"
            style={[styles.choice, styles.choiceApple]}
          >
            <Text style={[styles.choiceLabel, styles.choiceLabelOnDark]}>
              {t('onboarding.s16.apple')}
            </Text>
          </TouchableOpacity>
        ) : null}

        <TouchableOpacity
          testID="account-google"
          onPress={() => onSelectMethod('google')}
          accessibilityRole="button"
          style={[styles.choice, styles.choiceGoogle]}
        >
          <Text style={styles.choiceLabel}>{t('onboarding.s16.google')}</Text>
        </TouchableOpacity>

        <TouchableOpacity
          testID="account-email"
          onPress={() => onSelectMethod('email')}
          accessibilityRole="button"
          style={[styles.choice, styles.choiceEmail]}
        >
          <Text style={styles.choiceLabel}>{t('onboarding.s16.email')}</Text>
        </TouchableOpacity>
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
    alignItems: 'center',
    paddingTop: spacing['2xl'],
  },
  title: {
    ...typography.display,
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
  choices: {
    gap: spacing.md,
    paddingBottom: spacing.lg,
  },
  choice: {
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.lg,
    borderRadius: radii.button,
    minHeight: 48,
    alignItems: 'center',
    justifyContent: 'center',
  },
  choiceApple: {
    backgroundColor: colors.bg.inverse,
  },
  choiceGoogle: {
    backgroundColor: colors.bg.primary,
    borderWidth: 1,
    borderColor: colors.border.medium,
  },
  choiceEmail: {
    backgroundColor: colors.bg.secondary,
  },
  choiceLabel: {
    ...typography.body,
    fontWeight: '600',
    color: colors.text.primary,
  },
  choiceLabelOnDark: {
    color: colors.text.onInverse,
  },
});
