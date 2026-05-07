/**
 * StyleProfileCard
 *
 * Surfaces the user's cohort match on the Profile screen. Hidden when
 * `display` is null (low-confidence or population fallback per design
 * Section 5.6). Tapping the edit affordance opens the preferences
 * editor with an "inferred → user_stated" banner (B.6).
 */

import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { useTranslation } from 'react-i18next';
import { Card } from './Card';
import { colors, spacing, typography } from '../theme';
import type { CohortDisplayProfile } from '../services/api';

export interface StyleProfileCardProps {
  display: CohortDisplayProfile | null;
  onEditPress: () => void;
}

function joinPriorities(modal: CohortDisplayProfile['modal']): string {
  const parts = [modal.top_deciding_factor, modal.second_deciding_factor].filter(
    (p): p is string => Boolean(p)
  );
  return parts.join(', ');
}

export default function StyleProfileCard({ display, onEditPress }: StyleProfileCardProps) {
  const { t } = useTranslation();

  if (!display) return null;

  const priorities = joinPriorities(display.modal);

  // Phase 5 § 4d — confidence drives the strength label + progress
  // bar. high='Strong', medium='Building', low='Forming'. Bar fills
  // 1.0 / 0.66 / 0.33 to give a "tap to improve" affordance for
  // missing demographics.
  const strengthByConfidence: Record<'high' | 'medium' | 'low', {
    progress: number;
    labelKey: string;
    defaultValue: string;
  }> = {
    high: {
      progress: 1.0,
      labelKey: 'profile.styleProfile.strength.strong',
      defaultValue: 'Strong match',
    },
    medium: {
      progress: 0.66,
      labelKey: 'profile.styleProfile.strength.building',
      defaultValue: 'Building match',
    },
    low: {
      progress: 0.33,
      labelKey: 'profile.styleProfile.strength.forming',
      defaultValue: 'Forming match',
    },
  };
  const strength = strengthByConfidence[display.confidence];
  const governorate =
    typeof display.modal.governorate === 'string'
      ? display.modal.governorate
      : '';

  return (
    <Card style={styles.card}>
      {/* Phase 5 § 4d — match-strength eyebrow + sparkle + headline.
          Replaces the buried "STYLE PROFILE" eyebrow + persona label
          ordering. The persona label still appears below for context. */}
      <Text style={styles.eyebrow}>
        {t('profile.styleProfile.matchStrength', {
          defaultValue: 'Match strength',
        })}
      </Text>
      <Text testID="style-profile-strength-headline" style={styles.headline}>
        {t('profile.styleProfile.strengthHeadline', {
          strength: t(strength.labelKey, { defaultValue: strength.defaultValue }),
          defaultValue: `\u2728 ${strength.defaultValue}`,
        })}
      </Text>
      {governorate ? (
        <Text style={styles.subline}>
          {t('profile.styleProfile.peersInGovernorate', {
            count: display.n,
            governorate,
            defaultValue: `${display.n} peers in ${governorate}`,
          })}
        </Text>
      ) : (
        <Text style={styles.subline}>
          {t('profile.styleProfile.basedOn', { count: display.n })}
        </Text>
      )}

      {/* Strength progress bar — visual cue for "improve match" affordance. */}
      <View
        testID="style-profile-strength-bar"
        {...{ 'data-progress': strength.progress }}
        style={styles.progressTrack}
      >
        <View style={[styles.progressFill, { width: `${strength.progress * 100}%` }]} />
      </View>

      <Text style={styles.persona}>{display.persona_label}</Text>

      <View style={styles.divider} />

      {priorities ? (
        <View style={styles.row}>
          <Text style={styles.rowLabel}>{t('profile.styleProfile.priorities')}</Text>
          <Text style={styles.rowValue}>{priorities}</Text>
        </View>
      ) : null}

      {display.modal.spend_bracket ? (
        <View style={styles.row}>
          <Text style={styles.rowLabel}>{t('profile.styleProfile.budget')}</Text>
          <Text style={styles.rowValue}>{display.modal.spend_bracket}</Text>
        </View>
      ) : null}

      {display.modal.preferred_assistance_style ? (
        <View style={styles.row}>
          <Text style={styles.rowLabel}>{t('profile.styleProfile.style')}</Text>
          <Text style={styles.rowValue}>{display.modal.preferred_assistance_style}</Text>
        </View>
      ) : null}

      <TouchableOpacity
        accessibilityRole="button"
        style={styles.editButton}
        onPress={onEditPress}
      >
        <Text style={styles.editText}>
          {t('profile.styleProfile.editButton')}
        </Text>
      </TouchableOpacity>
    </Card>
  );
}

const styles = StyleSheet.create({
  card: {
    marginBottom: spacing.base,
  },
  /** Phase 5 § 4d — uppercase eyebrow above the match-strength headline. */
  eyebrow: {
    ...typography.caption,
    fontWeight: '600',
    color: colors.text.secondary,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: spacing.xs,
  },
  /** Sparkle + "Strong match" / "Building match" / "Forming match". */
  headline: {
    ...typography.title,
    color: colors.text.primary,
    marginBottom: spacing.xs,
  },
  /** "47 peers in Capital" or basedOn fallback. */
  subline: {
    ...typography.caption,
    color: colors.text.secondary,
    marginBottom: spacing.md,
  },
  /** Strength progress track + emerald fill. */
  progressTrack: {
    height: 4,
    backgroundColor: colors.border.light,
    borderRadius: 2,
    overflow: 'hidden',
    marginBottom: spacing.md,
  },
  progressFill: {
    height: 4,
    backgroundColor: colors.accent,
    borderRadius: 2,
  },
  /** Legacy "STYLE PROFILE" eyebrow — retained for back-compat with
      tests that still assert against `profile.styleProfile.title`.
      Hidden visually by overriding to no-op. */
  title: {
    height: 0,
    overflow: 'hidden',
  },
  persona: {
    ...typography.body,
    color: colors.text.primary,
    fontWeight: '600',
    marginBottom: spacing.xs,
  },
  basedOn: {
    ...typography.caption,
    color: colors.text.secondary,
  },
  divider: {
    height: 1,
    backgroundColor: colors.border.light,
    marginVertical: spacing.md,
  },
  row: {
    marginBottom: spacing.sm,
  },
  rowLabel: {
    ...typography.small,
    color: colors.text.secondary,
    fontWeight: '500',
    textTransform: 'uppercase',
    marginBottom: 2,
  },
  rowValue: {
    ...typography.body,
    color: colors.text.primary,
  },
  editButton: {
    marginTop: spacing.sm,
    alignSelf: 'flex-start',
  },
  editText: {
    ...typography.caption,
    color: colors.accent,
    fontWeight: '600',
  },
});
