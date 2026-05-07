/**
 * Step02Language — Phase 2 Task 13.
 *
 * "Choose your language / اختر لغتك" — sets RTL early so subsequent
 * screens render correctly. Two large cards: English / العربية.
 * See design spec § 2 row 2.
 */

import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { useTranslation } from 'react-i18next';
import { useLanguage } from '../../hooks/useLanguage';
import { colors, spacing, typography, radii } from '../../theme';

interface Props {
  /** Fired with the chosen language code AFTER switchLanguage() commits. */
  onChange: (lang: 'en' | 'ar') => void;
  /** Currently selected language (controls visual selected state). */
  value?: 'en' | 'ar';
}

export function Step02Language({ onChange, value }: Props) {
  const { t } = useTranslation();
  const { switchLanguage } = useLanguage();

  const select = (lang: 'en' | 'ar') => {
    // switchLanguage flips i18n + I18nManager + reloads via expo-updates.
    // Fire-and-forget: the orchestrator advances on the next tick.
    void switchLanguage(lang);
    onChange(lang);
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>{t('onboarding.s2.title')}</Text>

      <View style={styles.cardRow}>
        <LanguageCard
          testID="lang-en"
          label="English"
          selected={value === 'en'}
          onPress={() => select('en')}
        />
        <LanguageCard
          testID="lang-ar"
          label="العربية"
          selected={value === 'ar'}
          onPress={() => select('ar')}
        />
      </View>
    </View>
  );
}

interface LanguageCardProps {
  testID: string;
  label: string;
  selected: boolean;
  onPress: () => void;
}

function LanguageCard({ testID, label, selected, onPress }: LanguageCardProps) {
  return (
    <TouchableOpacity
      testID={testID}
      onPress={onPress}
      accessibilityRole="button"
      accessibilityState={{ selected }}
      style={[styles.card, selected && styles.cardSelected]}
    >
      <Text style={[styles.cardLabel, selected && styles.cardLabelSelected]}>
        {label}
      </Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    paddingHorizontal: spacing.xl,
    paddingTop: spacing['2xl'],
  },
  title: {
    ...typography.display,
    color: colors.text.primary,
    marginBottom: spacing['2xl'],
  },
  cardRow: {
    gap: spacing.md,
  },
  card: {
    backgroundColor: colors.bg.secondary,
    borderRadius: radii.card,
    paddingVertical: spacing.xl,
    paddingHorizontal: spacing.lg,
    borderWidth: 2,
    borderColor: 'transparent',
    alignItems: 'center',
  },
  cardSelected: {
    backgroundColor: colors.bg.primary,
    borderColor: colors.cta.primary,
  },
  cardLabel: {
    ...typography.title,
    color: colors.text.primary,
  },
  cardLabelSelected: {
    color: colors.text.primary,
  },
});
