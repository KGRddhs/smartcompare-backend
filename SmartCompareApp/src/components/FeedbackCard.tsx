/**
 * FeedbackCard - Inline feedback collection shown below comparison results
 * Restyled with Qaren design system (theme + i18n)
 */
import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  TextInput,
} from 'react-native';
import { ThumbsUp, ThumbsDown } from 'lucide-react-native';
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
  const [useful, setUseful] = useState<boolean | null>(null);
  const [matteredMost, setMatteredMost] = useState<string[]>([]);
  const [suggestion, setSuggestion] = useState('');
  const [submitting, setSubmitting] = useState(false);

  if (submitted) {
    return (
      <View style={styles.card}>
        <Text style={styles.thanksText}>{t('results.feedback.thanks')}</Text>
      </View>
    );
  }

  const toggleMattered = (item: string) => {
    setMatteredMost((prev) =>
      prev.includes(item) ? prev.filter((i) => i !== item) : [...prev, item]
    );
  };

  const handleSubmit = async () => {
    if (useful === null) return;
    setSubmitting(true);
    try {
      await submitFeedback({
        useful,
        comparison_id: comparisonId,
        mattered_most: matteredMost,
        change_suggestion: suggestion.trim() || undefined,
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

      {/* Thumbs up/down */}
      <View style={styles.thumbsRow}>
        <TouchableOpacity
          style={[styles.thumbButton, useful === true && styles.thumbSelected]}
          onPress={() => setUseful(true)}
        >
          <ThumbsUp size={20} color={useful === true ? colors.accent : colors.text.secondary} />
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.thumbButton, useful === false && styles.thumbSelectedNo]}
          onPress={() => setUseful(false)}
        >
          <ThumbsDown size={20} color={useful === false ? colors.destructive : colors.text.secondary} />
        </TouchableOpacity>
      </View>

      {/* Mattered most chips (optional) */}
      {useful !== null && (
        <>
          <View style={styles.chipsRow}>
            {MATTERED_OPTIONS.map((item) => (
              <TouchableOpacity
                key={item.key}
                style={[styles.chip, matteredMost.includes(item.key) && styles.chipSelected]}
                onPress={() => toggleMattered(item.key)}
              >
                <Text
                  style={[styles.chipText, matteredMost.includes(item.key) && styles.chipTextSelected]}
                >
                  {t(item.i18nKey)}
                </Text>
              </TouchableOpacity>
            ))}
          </View>

          {/* Optional text input */}
          <TextInput
            style={styles.textInput}
            placeholder="Tell us what could be better..."
            placeholderTextColor={colors.text.placeholder}
            value={suggestion}
            onChangeText={setSuggestion}
            multiline
            maxLength={500}
          />

          {/* Submit */}
          <TouchableOpacity
            style={[styles.submitButton, submitting && styles.submitDisabled]}
            onPress={handleSubmit}
            disabled={submitting}
          >
            <Text style={styles.submitText}>
              {submitting ? '...' : 'Submit'}
            </Text>
          </TouchableOpacity>
        </>
      )}
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
  title: {
    ...typography.body,
    fontWeight: '600',
    color: colors.text.primary,
    marginBottom: spacing.md,
  },
  thumbsRow: {
    flexDirection: 'row',
    gap: spacing.md,
    marginBottom: spacing.md,
  },
  thumbButton: {
    flex: 1,
    paddingVertical: spacing.md,
    borderRadius: radii.button,
    borderWidth: 1,
    borderColor: colors.border.light,
    alignItems: 'center',
    backgroundColor: colors.bg.primary,
  },
  thumbSelected: {
    backgroundColor: colors.accentLight,
    borderColor: colors.accent,
  },
  thumbSelectedNo: {
    backgroundColor: '#FEF2F2',
    borderColor: colors.destructive,
  },
  chipsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
    marginBottom: spacing.md,
  },
  chip: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs + 2,
    borderRadius: radii.chip,
    borderWidth: 1,
    borderColor: colors.border.light,
    backgroundColor: colors.bg.primary,
  },
  chipSelected: {
    backgroundColor: colors.accentLight,
    borderColor: colors.accent,
  },
  chipText: {
    ...typography.caption,
    color: colors.text.secondary,
  },
  chipTextSelected: {
    color: colors.accent,
    fontWeight: '600',
  },
  textInput: {
    backgroundColor: colors.bg.primary,
    borderRadius: radii.input,
    padding: spacing.md,
    ...typography.caption,
    color: colors.text.primary,
    marginBottom: spacing.md,
    minHeight: 60,
    textAlignVertical: 'top',
    borderWidth: 1,
    borderColor: colors.border.light,
  },
  submitButton: {
    backgroundColor: colors.accent,
    paddingVertical: spacing.md,
    borderRadius: radii.button,
    alignItems: 'center',
  },
  submitDisabled: {
    opacity: 0.5,
  },
  submitText: {
    color: '#FFFFFF',
    ...typography.body,
    fontWeight: '600',
  },
  thanksText: {
    ...typography.body,
    color: colors.accent,
    fontWeight: '500',
    textAlign: 'center',
  },
});
