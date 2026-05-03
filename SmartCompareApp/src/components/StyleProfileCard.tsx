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

  return (
    <Card style={styles.card}>
      <Text style={styles.title}>{t('profile.styleProfile.title')}</Text>
      <Text style={styles.persona}>{display.persona_label}</Text>
      <Text style={styles.basedOn}>
        {t('profile.styleProfile.basedOn', { count: display.n })}
      </Text>

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
  title: {
    ...typography.caption,
    fontWeight: '600',
    color: colors.text.secondary,
    textTransform: 'uppercase',
    marginBottom: spacing.xs,
  },
  persona: {
    ...typography.title,
    color: colors.text.primary,
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
