import React, { useState, useRef, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  SafeAreaView,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { ArrowLeft, Search } from 'lucide-react-native';
import { useTranslation } from 'react-i18next';
import { colors, spacing, radii, typography } from '../theme';
import { rtlFlip } from '../utils/rtl';

interface SearchOverlayProps {
  visible: boolean;
  onClose: () => void;
  onSubmit: (query: string) => void;
  recentSearches: string[];
}

// Bundle B/C/D Task 2.8 — comparison-shape detector. Plain "iPhone 15"
// shows the hint; "iPhone 15 vs Galaxy S24" or "X and Y" or "X, Y"
// hides it because the query is already comparison-shaped.
const COMPARISON_PATTERN = /\s(vs|&|and|or|أو|مقابل)\s|,/i;
export function looksLikeTwoProducts(raw: string): boolean {
  return COMPARISON_PATTERN.test(raw);
}

export function SearchOverlay({ visible, onClose, onSubmit, recentSearches }: SearchOverlayProps) {
  const { t } = useTranslation();
  const [query, setQuery] = useState('');
  const inputRef = useRef<TextInput>(null);

  useEffect(() => {
    if (visible) {
      setTimeout(() => inputRef.current?.focus(), 100);
    } else {
      setQuery('');
    }
  }, [visible]);

  if (!visible) return null;

  const handleSubmit = () => {
    const trimmed = query.trim();
    if (trimmed) onSubmit(trimmed);
  };

  const showNeedTwoHint = !looksLikeTwoProducts(query);

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        style={styles.inner}
      >
        <View style={styles.searchRow}>
          <TouchableOpacity onPress={onClose} style={rtlFlip()}>
            <ArrowLeft size={24} color={colors.text.primary} />
          </TouchableOpacity>
          <View style={styles.inputWrapper}>
            <Search size={18} color={colors.text.placeholder} />
            <TextInput
              testID="search-overlay-input"
              ref={inputRef}
              style={styles.input}
              placeholder={t('home.search.placeholder')}
              placeholderTextColor={colors.text.placeholder}
              value={query}
              onChangeText={setQuery}
              onSubmitEditing={handleSubmit}
              returnKeyType="search"
              autoCorrect={false}
            />
          </View>
        </View>

        {/* Bundle B/C/D Task 2.8 — gentle guidance until the query reads
            like a comparison ("X vs Y", "X, Y", "X and Y"). */}
        {showNeedTwoHint && (
          <View testID="search-need-two-hint" style={styles.hintBanner}>
            <Text style={styles.hintText}>
              {t('home.search.needTwoHint')}
            </Text>
          </View>
        )}

        {recentSearches.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>{t('home.search.recent')}</Text>
            {recentSearches.slice(0, 5).map((search, i) => (
              <TouchableOpacity
                key={i}
                style={styles.searchItem}
                onPress={() => onSubmit(search)}
              >
                <Text style={styles.searchItemText}>{search}</Text>
              </TouchableOpacity>
            ))}
          </View>
        )}
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg.primary },
  inner: { flex: 1 },
  searchRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    gap: spacing.md,
  },
  inputWrapper: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.bg.secondary,
    borderRadius: radii.input,
    paddingHorizontal: spacing.md,
    gap: spacing.sm,
    borderWidth: 1,
    borderColor: colors.border.light,
  },
  input: {
    flex: 1,
    ...typography.body,
    color: colors.text.primary,
    paddingVertical: spacing.md,
    textAlign: 'auto',
  },
  section: { paddingHorizontal: spacing.lg, paddingTop: spacing.lg },
  sectionTitle: { ...typography.caption, color: colors.text.secondary, fontWeight: '600', marginBottom: spacing.sm },
  searchItem: { paddingVertical: spacing.md },
  searchItemText: { ...typography.body, color: colors.text.primary },
  // Bundle B/C/D Task 2.8 — guidance banner.
  hintBanner: {
    marginHorizontal: spacing.lg,
    marginTop: spacing.sm,
    padding: spacing.md,
    backgroundColor: colors.bg.secondary,
    borderRadius: radii.button,
  },
  hintText: {
    ...typography.caption,
    color: colors.text.secondary,
    textAlign: 'center',
  },
});

export default SearchOverlay;
