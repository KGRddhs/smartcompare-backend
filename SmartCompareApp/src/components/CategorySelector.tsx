import React from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  ScrollView,
  StyleSheet,
} from 'react-native';

interface CategorySelectorProps {
  value: string | null;
  onChange: (category: string) => void;
}

interface Category {
  value: string;
  label: string;
  icon: string;
}

const CATEGORIES: Category[] = [
  { value: 'electronics', label: 'Electronics', icon: '\u{1F4F1}' },
  { value: 'grocery', label: 'Grocery', icon: '\u{1F6D2}' },
  { value: 'supplements', label: 'Supplements', icon: '\u{1F48A}' },
  { value: 'makeup', label: 'Makeup', icon: '\u{1F484}' },
  { value: 'skincare', label: 'Skincare', icon: '\u2728' },
  { value: 'haircare', label: 'Haircare', icon: '\u{1F487}' },
  { value: 'fragrances', label: 'Fragrances', icon: '\u{1F338}' },
  { value: 'fashion', label: 'Fashion', icon: '\u{1F45C}' },
];

export default function CategorySelector({ value, onChange }: CategorySelectorProps) {
  return (
    <View style={styles.container}>
      <Text style={styles.label}>What are you comparing?</Text>
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
                {cat.label}
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
    marginBottom: 16,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
    marginBottom: 8,
    paddingHorizontal: 4,
  },
  scrollContent: {
    paddingHorizontal: 4,
  },
  chip: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FFF',
    borderRadius: 20,
    paddingVertical: 8,
    paddingHorizontal: 14,
    marginRight: 8,
    borderWidth: 1,
    borderColor: '#E0E0E0',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 1,
  },
  chipActive: {
    backgroundColor: '#007AFF',
    borderColor: '#007AFF',
    shadowOpacity: 0.15,
    shadowRadius: 4,
    elevation: 3,
  },
  chipIcon: {
    fontSize: 16,
    marginRight: 6,
  },
  chipText: {
    fontSize: 13,
    fontWeight: '500',
    color: '#333',
  },
  chipTextActive: {
    color: '#FFF',
    fontWeight: '600',
  },
});
