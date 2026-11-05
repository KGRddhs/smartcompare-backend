import React from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  ScrollView,
  StyleSheet,
} from 'react-native';
import { useTranslation } from 'react-i18next';
// Bundle B/C/D Task 2.9 — per-icon lucide imports (NOT barrel) preserve
// tree-shaking. See plan § Task 2.9 + design § 4 "lucide imports".
import {
  Smartphone,
  ShoppingCart,
  Pill,
  Brush,
  Sparkles,
  Scissors,
  Flower,
  ShoppingBag,
  Package,
} from 'lucide-react-native';
import { colors, spacing, radii, typography } from '../theme';

interface CategorySelectorProps {
  value: string | null;
  onChange: (category: string) => void;
  /** S81-11: coming-soon chips, only where /app/version `surfaces` says so. */
  surfaces?: { skincare: boolean; makeup: boolean };
  onComingSoon?: (key: 'skincare' | 'makeup') => void;
}

type Launch = 'live' | 'surface' | 'hidden';

type LucideIcon = React.ComponentType<{ size?: number; color?: string }>;

interface Category {
  value: string;
  i18nKey: string;
  Icon: LucideIcon;
  launch: Launch;
}

const CATEGORIES: Category[] = [
  { value: 'electronics', i18nKey: 'home.categories.electronics', Icon: Smartphone, launch: 'hidden' },
  { value: 'grocery', i18nKey: 'home.categories.grocery', Icon: ShoppingCart, launch: 'hidden' },
  { value: 'supplements', i18nKey: 'home.categories.supplements', Icon: Pill, launch: 'hidden' },
  // Lucide ships no Lipstick glyph at this version; Brush is the closest
  // makeup-applicator metaphor that's broadly recognized.
  { value: 'makeup', i18nKey: 'home.categories.makeup', Icon: Brush, launch: 'surface' },
  { value: 'skincare', i18nKey: 'home.categories.skincare', Icon: Sparkles, launch: 'surface' },
  { value: 'haircare', i18nKey: 'home.categories.haircare', Icon: Scissors, launch: 'hidden' },
  { value: 'fragrances', i18nKey: 'home.categories.fragrances', Icon: Flower, launch: 'live' },
  { value: 'fashion', i18nKey: 'home.categories.fashion', Icon: ShoppingBag, launch: 'hidden' },
  { value: 'other', i18nKey: 'home.categories.other', Icon: Package, launch: 'hidden' },
];

const SURFACE_CHIP_KEYS = ['skincare', 'makeup'] as const;

export default function CategorySelector({
  value,
  onChange,
  surfaces,
  onComingSoon,
}: CategorySelectorProps) {
  const { t } = useTranslation();
  const live = CATEGORIES.filter((c) => c.launch === 'live');
  const soon = SURFACE_CHIP_KEYS.filter((k) => surfaces?.[k] === true && !!onComingSoon)
    .map((k) => CATEGORIES.find((c) => c.value === k))
    .filter((c): c is Category => !!c);

  return (
    <View style={styles.container}>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.scrollContent}
      >
        {live.map((cat) => {
          const isSelected = value === cat.value;
          const iconColor = isSelected ? '#FFFFFF' : colors.text.primary;
          return (
            <TouchableOpacity
              key={cat.value}
              testID={`category-chip-${cat.value}`}
              style={[styles.chip, isSelected && styles.chipActive]}
              onPress={() => onChange(cat.value)}
              activeOpacity={0.7}
              accessibilityRole="button"
              accessibilityState={{ selected: isSelected }}
              accessibilityLabel={t(cat.i18nKey)}
            >
              <cat.Icon size={16} color={iconColor} />
              <Text
                style={[
                  styles.chipText,
                  isSelected && styles.chipTextActive,
                ]}
              >
                {t(cat.i18nKey)}
              </Text>
            </TouchableOpacity>
          );
        })}
        {soon.map((cat) => (
          <TouchableOpacity
            key={cat.value}
            testID={`category-chip-${cat.value}`}
            style={styles.chip}
            onPress={() => onComingSoon?.(cat.value as 'skincare' | 'makeup')}
            activeOpacity={0.7}
            accessibilityRole="button"
            accessibilityState={{ disabled: false, selected: false }}
            accessibilityLabel={t(cat.i18nKey)}
            accessibilityHint={t('home.categories.comingSoon')}
          >
            <cat.Icon size={16} color={colors.text.secondary} />
            <Text style={styles.chipText}>{t(cat.i18nKey)}</Text>
            <Text testID={`category-chip-${cat.value}-soon`} style={styles.chipText}>
              {t('home.categories.comingSoon')}
            </Text>
          </TouchableOpacity>
        ))}
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
    gap: spacing.xs,
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
