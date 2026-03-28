import React from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  ScrollView,
  StyleSheet,
} from 'react-native';
import { useTranslation } from 'react-i18next';
import { colors, spacing, radii, typography } from '../theme';

interface CategorySelectorProps {
  value: string | null;
  onChange: (category: string) => void;
}

interface Category {
  value: string;
  i18nKey: string;
  icon: string;
}

const CATEGORIES: Category[] = [
  { value: 'electronics', i18nKey: 'home.categories.electronics', icon: '\u{1F4F1}' },
  { value: 'grocery', i18nKey: 'home.categories.grocery', icon: '\u{1F6D2}' },
  { value: 'supplements', i18nKey: 'home.categories.supplements', icon: '\u{1F48A}' },
  { value: 'makeup', i18nKey: 'home.categories.makeup', icon: '\u{1F484}' },
  { value: 'skincare', i18nKey: 'home.categories.skincare', icon: '\u2728' },
  { value: 'haircare', i18nKey: 'home.categories.haircare', icon: '\u{1F487}' },
  { value: 'fragrances', i18nKey: 'home.categories.fragrances', icon: '\u{1F338}' },
  { value: 'fashion', i18nKey: 'home.categories.fashion', icon: '\u{1F45C}' },
  { value: 'other', i18nKey: 'home.categories.other', icon: '\u{1F4E6}' },
];

export default function CategorySelector({ value, onChange }: CategorySelectorProps) {
  const { t } = useTranslation();

  return (
    <View style={styles.container}>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.scrollContent}
      >
        {CATEGORIES.map((cat) => {
          const isSelected = value === cat.value;
          return (
            <TouchableOpacity
              key={cat.value}
              testID={`category-chip-${cat.value}`}
              style={[styles.chip, isSelected && styles.chipActive]}
              onPress={() => onChange(cat.value)}
              activeOpacity={0.7}
            >
              <Text style={styles.chipIcon}>{cat.icon}</Text>
              <Text style={[styles.chipText, isSelected && styles.chipTextActive]}>
                {t(cat.i18nKey)}
              </Text>
            </TouchableOpacity>
          );
        })}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    marginBottom: spacing.base,
  },
  scrollContent: {
    paddingHorizontal: spacing.xs,
    gap: spacing.sm,
  },
  chip: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.bg.secondary,
    borderRadius: radii.chip,
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.base,
    borderWidth: 1,
    borderColor: colors.border.light,
  },
  chipActive: {
    backgroundColor: colors.accent,
    borderColor: colors.accent,
  },
  chipIcon: {
    fontSize: 16,
    marginEnd: spacing.xs,
  },
  chipText: {
    ...typography.caption,
    fontWeight: '500',
    color: colors.text.primary,
  },
  chipTextActive: {
    color: '#FFFFFF',
    fontWeight: '600',
  },
});
