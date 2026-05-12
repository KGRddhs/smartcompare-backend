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
}

type LucideIcon = React.ComponentType<{ size?: number; color?: string }>;

interface Category {
  value: string;
  i18nKey: string;
  Icon: LucideIcon;
}

const CATEGORIES: Category[] = [
  { value: 'electronics', i18nKey: 'home.categories.electronics', Icon: Smartphone },
  { value: 'grocery', i18nKey: 'home.categories.grocery', Icon: ShoppingCart },
  { value: 'supplements', i18nKey: 'home.categories.supplements', Icon: Pill },
  // Lucide ships no Lipstick glyph at this version; Brush is the closest
  // makeup-applicator metaphor that's broadly recognized.
  { value: 'makeup', i18nKey: 'home.categories.makeup', Icon: Brush },
  { value: 'skincare', i18nKey: 'home.categories.skincare', Icon: Sparkles },
  { value: 'haircare', i18nKey: 'home.categories.haircare', Icon: Scissors },
  { value: 'fragrances', i18nKey: 'home.categories.fragrances', Icon: Flower },
  { value: 'fashion', i18nKey: 'home.categories.fashion', Icon: ShoppingBag },
  { value: 'other', i18nKey: 'home.categories.other', Icon: Package },
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
