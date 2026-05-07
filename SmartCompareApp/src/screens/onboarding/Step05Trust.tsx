/**
 * Step05Trust — Phase 2 Task 14.
 *
 * Trust bridge — pure typography + small filled lock icon (rotates 5° on
 * mount per design spec, deferred to on-device polish). Hero copy "Your
 * data stays yours. We just compare." + 3 thin bullets.
 *
 * Pre-empts the "why do you need this?" objection BEFORE we ask for age,
 * gender, etc. Copy strictly follows § 4g audit ("Your data lives on your
 * device", "We match anonymously — no name attached", "Skip anything —
 * and edit later").
 */

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useTranslation } from 'react-i18next';
import { Button } from '../../components/Button';
import { colors, spacing, typography, radii } from '../../theme';

interface Props {
  onNext: () => void;
}

export function Step05Trust({ onNext }: Props) {
  const { t } = useTranslation();

  return (
    <View style={styles.container}>
      <View style={styles.heroBlock}>
        <View style={styles.lockBadge} testID="trust-lock-icon">
          {/* Geometric lock glyph; replaced by full custom icon in Phase 5
              when the icon system rounds out. The 5° rotation animation
              also lives on Phase 5 polish. */}
          <Text style={styles.lockGlyph}>{'\u{1F512}'}</Text>
        </View>

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
