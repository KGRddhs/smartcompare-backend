/**
 * FeedbackCard - Inline feedback collection shown below comparison results.
 *
 * Source of truth: docs/claude-design-handoff/ui_kits/mobile/ResultsScreen.jsx
 * Feedback prompt (JSX 384-404) — a "Was this helpful?" title + a single
 * row of three pill chips: Accurate / Detailed / Fast. The reference shows
 * ONLY those chips (no thumbs up/down, no free-text box). Tapping a chip
 * records it as a positive-helpful signal (`useful: true` + the chip in
 * `mattered_most`) and fires the existing feedback event, then shows the
 * thanks state.
 */
import React, { useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { useTranslation } from 'react-i18next';
import { colors, spacing, radii, typography, shadows } from '../theme';
import { submitFeedback } from '../services/api';

const MATTERED_OPTIONS = [
  { key: 'accurate', i18nKey: 'results.feedback.accurate' },
  { key: 'detailed', i18nKey: 'results.feedback.detailed' },
  { key: 'fast', i18nKey: 'results.feedback.fast' },
] as const;

interface FeedbackCardProps {
  comparisonId?: string;
  submitted?: boolean;
  onSubmitted?: () => void;
}

export default function FeedbackCard({ comparisonId, submitted: parentSubmitted, onSubmitted }: FeedbackCardProps) {
  const { t } = useTranslation();
  const [localSubmitted, setLocalSubmitted] = useState(false);
  const submitted = parentSubmitted ?? localSubmitted;
  const [submitting, setSubmitting] = useState(false);

  if (submitted) {
    return (
      <View style={styles.card}>
        <Text style={styles.thanksText}>{t('results.feedback.thanks')}</Text>
      </View>
    );
  }

  // Tapping a chip fires the feedback event (fire-and-forget) with a
  // positive-helpful signal + the chosen quality in mattered_most, then
  // shows the thanks state. One tap = one submission, matching the
  // reference's single-row chip control.
  const handleChip = async (chipKey: string) => {
    if (submitting) return;
    setSubmitting(true);
    try {
      await submitFeedback({
        useful: true,
        comparison_id: comparisonId,
        mattered_most: [chipKey],
      });
    } catch {
      // Fire-and-forget
    }
    setLocalSubmitted(true);
    onSubmitted?.();
    setSubmitting(false);
  };

  return (
    <View style={styles.card}>
      <Text style={styles.title}>{t('results.feedback.title')}</Text>
      <View style={styles.chipsRow}>
        {MATTERED_OPTIONS.map((item) => (
          <TouchableOpacity
            key={item.key}
            testID={`feedback-chip-${item.key}`}
            accessibilityRole="button"
            style={styles.chip}
            onPress={() => handleChip(item.key)}
            disabled={submitting}
            activeOpacity={0.7}
          >
            <Text style={styles.chipText}>{t(item.i18nKey)}</Text>
          </TouchableOpacity>
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.bg.secondary,
    marginHorizontal: spacing.base,
    marginVertical: spacing.sm,
    padding: spacing.base,
    borderRadius: radii.card,
    borderWidth: 1,
    borderColor: colors.border.light,
    ...shadows.card,
  },
  // Reference: feedback prompt title (ResultsScreen.jsx 389) — 15/600.
  title: {
    fontSize: 15,
    fontWeight: '600',
    color: colors.text.primary,
    marginBottom: spacing.sm + 2,
  },
  chipsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
  },
  // Reference chip (ResultsScreen.jsx 394-401): pill, bg.primary on the
  // card's bg.secondary, hairline border, 36px tall, 13/500 text.primary.
  chip: {
    paddingHorizontal: 14,
    height: 36,
    justifyContent: 'center',
    borderRadius: radii.chip,
    borderWidth: 1,
    borderColor: colors.border.light,
    backgroundColor: colors.bg.primary,
  },
  chipText: {
    fontSize: 13,
    fontWeight: '500',
    color: colors.text.primary,
  },
  thanksText: {
    ...typography.body,
    color: colors.accent,
    fontWeight: '500',
    textAlign: 'center',
  },
});
