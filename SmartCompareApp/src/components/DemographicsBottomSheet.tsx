/**
 * DemographicsBottomSheet
 *
 * Post-first-comparison prompt asking three optional demographic questions
 * (age group, gender, governorate). Auto-detects language from device locale.
 * Skipped fields default to "Prefer not to say" so the backend can fall back
 * to broader cohort aggregates.
 *
 * Trigger / dismissal cooldown lives in services/demographicsTrigger.ts.
 */

import React, { useMemo, useState } from 'react';
import {
  View,
  Text,
  Modal,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  Platform,
} from 'react-native';
import * as Localization from 'expo-localization';
import * as Haptics from 'expo-haptics';
import { useTranslation } from 'react-i18next';
import { Chip } from './Chip';
import { colors, spacing, radii, typography } from '../theme';
import type { DemographicsPayload } from '../services/api';

const PREFER_NOT_TO_SAY = 'Prefer not to say';

interface QuestionSpec {
  key: 'age_group' | 'gender' | 'governorate';
  labelKey: string;
  options: { value: string; labelKey: string }[];
}

const QUESTIONS: QuestionSpec[] = [
  {
    key: 'age_group',
    labelKey: 'demographics.age',
    options: [
      { value: '18-24', labelKey: 'demographics.age.18_24' },
      { value: '25-34', labelKey: 'demographics.age.25_34' },
      { value: '35-44', labelKey: 'demographics.age.35_44' },
      { value: '45-54', labelKey: 'demographics.age.45_54' },
      { value: '55+', labelKey: 'demographics.age.55_plus' },
    ],
  },
  {
    key: 'gender',
    labelKey: 'demographics.gender',
    options: [
      { value: 'Female', labelKey: 'demographics.gender.female' },
      { value: 'Male', labelKey: 'demographics.gender.male' },
    ],
  },
  {
    key: 'governorate',
    labelKey: 'demographics.governorate',
    options: [
      { value: 'Capital', labelKey: 'demographics.governorate.capital' },
      { value: 'Muharraq', labelKey: 'demographics.governorate.muharraq' },
      { value: 'Northern', labelKey: 'demographics.governorate.northern' },
      { value: 'Southern', labelKey: 'demographics.governorate.southern' },
      { value: 'Other', labelKey: 'demographics.governorate.other' },
    ],
  },
];

function detectLanguage(): 'Arabic' | 'English' | 'Both equally' {
  try {
    const code = (Localization as any).locale ?? '';
    if (typeof code === 'string') {
      if (code.toLowerCase().startsWith('ar')) return 'Arabic';
      if (code.toLowerCase().startsWith('en')) return 'English';
    }
    const locales = (Localization as any).getLocales?.();
    const lang = Array.isArray(locales) ? locales[0]?.languageCode : null;
    if (lang === 'ar') return 'Arabic';
    if (lang === 'en') return 'English';
  } catch {
    // fall through
  }
  return 'Both equally';
}

export interface DemographicsBottomSheetProps {
  visible: boolean;
  onSubmit: (payload: DemographicsPayload) => Promise<void> | void;
  onSkip: () => void;
  errorMessage?: string | null;
}

export default function DemographicsBottomSheet({
  visible,
  onSubmit,
  onSkip,
  errorMessage,
}: DemographicsBottomSheetProps) {
  const { t } = useTranslation();
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);

  const detectedLanguage = useMemo(() => detectLanguage(), []);

  const handleSelect = (key: QuestionSpec['key'], value: string) => {
    try {
      Haptics.selectionAsync();
    } catch {
      // haptics optional
    }
    setAnswers((prev) => ({ ...prev, [key]: value }));
  };

  const handleSave = async () => {
    if (submitting) return;
    setSubmitting(true);
    const payload: DemographicsPayload = {
      age_group: answers.age_group ?? PREFER_NOT_TO_SAY,
      gender: answers.gender ?? PREFER_NOT_TO_SAY,
      governorate: answers.governorate ?? PREFER_NOT_TO_SAY,
      language: detectedLanguage,
    };
    try {
      await onSubmit(payload);
    } finally {
      setSubmitting(false);
    }
  };

  const handleSkip = () => {
    if (submitting) return;
    onSkip();
  };

  if (!visible) return null;

  return (
    <Modal
      visible={visible}
      transparent
      animationType="slide"
      onRequestClose={handleSkip}
    >
      <View style={styles.overlay}>
        <View style={styles.sheet} accessibilityViewIsModal>
          <View style={styles.handle} />
          <Text style={styles.title}>{t('demographics.title')}</Text>
          <Text style={styles.subtitle}>{t('demographics.subtitle')}</Text>

          <ScrollView
            contentContainerStyle={styles.scrollContent}
            showsVerticalScrollIndicator={false}
          >
            {QUESTIONS.map((q) => (
              <View key={q.key} style={styles.questionBlock}>
                <Text style={styles.questionLabel}>{t(q.labelKey)}</Text>
                <View style={styles.chipsRow}>
                  {q.options.map((opt) => (
                    <Chip
                      key={opt.value}
                      label={t(opt.labelKey)}
                      selected={answers[q.key] === opt.value}
                      onPress={() => handleSelect(q.key, opt.value)}
                      disabled={submitting}
                    />
                  ))}
                  <Chip
                    key="prefer-not-to-say"
                    label={t('demographics.preferNotToSay')}
                    selected={answers[q.key] === PREFER_NOT_TO_SAY}
                    onPress={() => handleSelect(q.key, PREFER_NOT_TO_SAY)}
                    disabled={submitting}
                  />
                </View>
              </View>
            ))}
          </ScrollView>

          {errorMessage ? (
            <Text style={styles.errorText}>{errorMessage}</Text>
          ) : null}

          <View style={styles.actions}>
            <TouchableOpacity
              accessibilityRole="button"
              style={[styles.skipButton, submitting && styles.disabledOpacity]}
              onPress={handleSkip}
              disabled={submitting}
            >
              <Text style={styles.skipText}>{t('demographics.skip')}</Text>
            </TouchableOpacity>
            <TouchableOpacity
              accessibilityRole="button"
              style={[styles.saveButton, submitting && styles.disabledOpacity]}
              onPress={handleSave}
              disabled={submitting}
            >
              {submitting ? (
                <ActivityIndicator size="small" color={colors.bg.primary} />
              ) : (
                <Text style={styles.saveText}>{t('demographics.save')}</Text>
              )}
            </TouchableOpacity>
          </View>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.4)',
    justifyContent: 'flex-end',
  },
  sheet: {
    backgroundColor: colors.bg.primary,
    borderTopStartRadius: spacing.xl,
    borderTopEndRadius: spacing.xl,
    paddingTop: spacing.md,
    paddingHorizontal: spacing.lg,
    paddingBottom: Platform.OS === 'ios' ? spacing['3xl'] : spacing.xl,
    maxHeight: '85%',
  },
  handle: {
    width: 40,
    height: 4,
    backgroundColor: colors.border.medium,
    borderRadius: 2,
    alignSelf: 'center',
    marginBottom: spacing.lg,
  },
  title: {
    ...typography.title,
    color: colors.text.primary,
    textAlign: 'center',
  },
  subtitle: {
    ...typography.caption,
    color: colors.text.secondary,
    textAlign: 'center',
    marginTop: spacing.xs,
    marginBottom: spacing.lg,
  },
  scrollContent: {
    paddingBottom: spacing.base,
  },
  questionBlock: {
    marginBottom: spacing.base,
  },
  questionLabel: {
    ...typography.body,
    fontWeight: '600',
    color: colors.text.primary,
    marginBottom: spacing.sm,
  },
  chipsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.xs,
  },
  errorText: {
    ...typography.small,
    color: colors.destructive,
    textAlign: 'center',
    marginBottom: spacing.sm,
  },
  actions: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: spacing.base,
    gap: spacing.sm,
  },
  skipButton: {
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.lg,
  },
  skipText: {
    ...typography.body,
    color: colors.text.secondary,
    fontWeight: '500',
  },
  saveButton: {
    flexGrow: 1,
    backgroundColor: colors.accent,
    paddingVertical: spacing.md,
    borderRadius: radii.button,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 48,
  },
  saveText: {
    ...typography.body,
    fontWeight: '600',
    color: '#FFFFFF',
  },
  disabledOpacity: {
    opacity: 0.6,
  },
});
