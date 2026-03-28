/**
 * Qaren - History Screen
 * Past comparisons with date grouping, search, delete, and staggered animation
 */

import React, { useEffect, useState, useCallback, useMemo } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  SafeAreaView,
  ActivityIndicator,
  RefreshControl,
  Alert,
  TextInput,
  SectionList,
} from 'react-native';
import { useTranslation } from 'react-i18next';
import { useFocusEffect } from '@react-navigation/native';
import { Search, Trash2, RotateCcw, ChevronRight, Camera } from 'lucide-react-native';
import Animated, { FadeInDown } from 'react-native-reanimated';
import { colors, spacing, radii, typography, shadows } from '../theme';
import { getComparisonHistory, deleteComparison, parseApiError } from '../services/api';
import { clearSession } from '../services/authService';

interface HistoryItem {
  id: string;
  full_response: any;
  query: string;
  input_type: string;
  product_names: string[];
  created_at: string;
}

interface HistorySection {
  title: string;
  data: HistoryItem[];
}

interface HistoryScreenProps {
  navigation: any;
  onLogout: () => void;
}

export default function HistoryScreen({ navigation, onLogout }: HistoryScreenProps) {
  const { t } = useTranslation();
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [total, setTotal] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [authError, setAuthError] = useState(false);

  useFocusEffect(
    useCallback(() => {
      loadHistory();
    }, [])
  );

  const loadHistory = async () => {
    try {
      setAuthError(false);
      const data = await getComparisonHistory(50, 0, searchQuery || undefined);
      setHistory(data.comparisons || []);
      setTotal(data.total || 0);
    } catch (error) {
      const status = (error as any)?.response?.status;
      if (status === 401) {
        setAuthError(true);
        setHistory([]);
        setTotal(0);
      } else {
        console.error('Error loading history:', error);
        Alert.alert(t('common.error'), parseApiError(error).message);
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const onRefresh = () => {
    setRefreshing(true);
    loadHistory();
  };

  const getDateGroup = (dateString: string): string => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffDays === 0) return t('history.today');
    if (diffDays === 1) return t('history.yesterday');
    if (diffDays < 7) return t('history.thisWeek');
    return t('history.older');
  };

  const formatTimeAgo = (dateString: string): string => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return t('history.ago', { time: '<1m' });
    if (diffMins < 60) return t('history.ago', { time: `${diffMins}m` });
    if (diffHours < 24) return t('history.ago', { time: `${diffHours}h` });
    if (diffDays < 7) return t('history.ago', { time: `${diffDays}d` });

    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined,
    });
  };

  const formatPrice = (product: any): string => {
    if (!product || product.price === null || product.price === undefined) return 'N/A';
    if (typeof product.price === 'object') {
      if (product.price.amount === null || product.price.amount === undefined) return 'N/A';
      return `${product.price.amount.toFixed(2)} ${product.price.currency || 'BHD'}`;
    }
    return `${(product.price as number).toFixed(2)} BHD`;
  };

  const sections: HistorySection[] = useMemo(() => {
    const groups: Record<string, HistoryItem[]> = {};
    const order = [t('history.today'), t('history.yesterday'), t('history.thisWeek'), t('history.older')];

    for (const item of history) {
      const group = getDateGroup(item.created_at);
      if (!groups[group]) groups[group] = [];
      groups[group].push(item);
    }

    return order
      .filter((title) => groups[title]?.length)
      .map((title) => ({ title, data: groups[title] }));
  }, [history, t]);

  const viewAsResult = (item: HistoryItem) => {
    navigation.navigate('Results', { result: item.full_response });
  };

  const handleDelete = (item: HistoryItem) => {
    Alert.alert(
      t('history.delete'),
      t('profile.deleteConfirm'),
      [
        { text: t('common.cancel'), style: 'cancel' },
        {
          text: t('history.delete'),
          style: 'destructive',
          onPress: async () => {
            try {
              await deleteComparison(item.id);
              setHistory((prev) => prev.filter((h) => h.id !== item.id));
              setTotal((prev) => prev - 1);
            } catch {
              Alert.alert(t('common.error'), 'Failed to delete comparison');
            }
          },
        },
      ]
    );
  };

  const renderItem = ({ item, index }: { item: HistoryItem; index: number }) => {
    const products = item.full_response?.products || [];
    const winnerIndex = item.full_response?.comparison?.winner_index ?? item.full_response?.winner_index ?? 0;
    const winner = products[winnerIndex];

    return (
      <Animated.View entering={FadeInDown.delay(index * 50).duration(300)}>
        <TouchableOpacity
          style={styles.card}
          onPress={() => viewAsResult(item)}
          activeOpacity={0.7}
        >
          <View style={styles.cardContent}>
            <View style={styles.cardTop}>
              <Text style={styles.cardQuery} numberOfLines={1}>
                {products[0]?.brand} {products[0]?.name} vs {products[1]?.brand} {products[1]?.name}
              </Text>
              <Text style={styles.cardTime}>{formatTimeAgo(item.created_at)}</Text>
            </View>

            {winner && (
              <Text style={styles.cardWinner} numberOfLines={1}>
                {t('history.winner', { name: `${winner.brand} ${winner.name}` })} · {formatPrice(winner)}
              </Text>
            )}
          </View>

          <View style={styles.cardActions}>
            <TouchableOpacity
              style={styles.actionButton}
              onPress={() => handleDelete(item)}
              hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
            >
              <Trash2 size={16} color={colors.text.secondary} />
            </TouchableOpacity>
            <ChevronRight size={16} color={colors.text.placeholder} />
          </View>
        </TouchableOpacity>
      </Animated.View>
    );
  };

  const renderSectionHeader = ({ section }: { section: HistorySection }) => (
    <Text style={styles.sectionHeader}>{section.title}</Text>
  );

  const renderEmpty = () => (
    <View style={styles.emptyContainer}>
      <View style={styles.emptyIcon}>
        <Camera size={32} color={colors.text.placeholder} />
        <Search size={20} color={colors.text.placeholder} style={{ marginStart: -8, marginTop: -8 }} />
      </View>
      <Text style={styles.emptyTitle}>{t('history.empty.title')}</Text>
      <TouchableOpacity
        style={styles.emptyCta}
        onPress={() => navigation.navigate('HomeTab')}
      >
        <Text style={styles.emptyCtaText}>{t('history.empty.cta')}</Text>
        <ChevronRight size={16} color={colors.bg.primary} />
      </TouchableOpacity>
    </View>
  );

  const renderAuthError = () => (
    <View style={styles.authContainer}>
      <Text style={styles.authTitle}>{t('common.signInRequired')}</Text>
      <TouchableOpacity
        style={styles.authButton}
        onPress={async () => {
          await clearSession();
          onLogout();
        }}
      >
        <Text style={styles.authButtonText}>{t('auth.signIn')}</Text>
      </TouchableOpacity>
    </View>
  );

  if (loading) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={colors.accent} />
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>{t('history.title')}</Text>
      </View>

      <View style={styles.searchContainer}>
        <Search size={16} color={colors.text.placeholder} />
        <TextInput
          style={styles.searchInput}
          placeholder={t('history.search')}
          placeholderTextColor={colors.text.placeholder}
          value={searchQuery}
          onChangeText={setSearchQuery}
          onSubmitEditing={() => {
            setLoading(true);
            loadHistory();
          }}
          returnKeyType="search"
        />
      </View>

      {authError ? (
        renderAuthError()
      ) : history.length === 0 ? (
        renderEmpty()
      ) : (
        <SectionList
          sections={sections}
          renderItem={renderItem}
          renderSectionHeader={renderSectionHeader}
          keyExtractor={(item) => item.id}
          contentContainerStyle={styles.listContent}
          stickySectionHeadersEnabled={false}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={onRefresh}
              tintColor={colors.accent}
            />
          }
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bg.primary,
  },
  header: {
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.base,
    paddingBottom: spacing.md,
  },
  headerTitle: {
    ...typography.display,
    color: colors.text.primary,
  },
  searchContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginHorizontal: spacing.lg,
    marginBottom: spacing.base,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    backgroundColor: colors.bg.secondary,
    borderRadius: radii.input,
    gap: spacing.sm,
  },
  searchInput: {
    flex: 1,
    ...typography.body,
    color: colors.text.primary,
    paddingVertical: 0,
  },
  listContent: {
    paddingHorizontal: spacing.lg,
    paddingBottom: spacing['3xl'],
  },
  sectionHeader: {
    ...typography.caption,
    fontWeight: '600',
    color: colors.text.secondary,
    textTransform: 'uppercase',
    marginTop: spacing.lg,
    marginBottom: spacing.sm,
  },
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.bg.secondary,
    borderRadius: radii.card,
    padding: spacing.base,
    marginBottom: spacing.sm,
  },
  cardContent: {
    flex: 1,
  },
  cardTop: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.xs,
  },
  cardQuery: {
    ...typography.body,
    fontWeight: '600',
    color: colors.text.primary,
    flex: 1,
    marginEnd: spacing.sm,
  },
  cardTime: {
    ...typography.small,
    color: colors.text.secondary,
  },
  cardWinner: {
    ...typography.caption,
    color: colors.text.secondary,
  },
  cardActions: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    marginStart: spacing.md,
  },
  actionButton: {
    padding: spacing.xs,
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: spacing['2xl'],
  },
  emptyIcon: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    marginBottom: spacing.lg,
  },
  emptyTitle: {
    ...typography.title,
    color: colors.text.primary,
    textAlign: 'center',
    marginBottom: spacing.xl,
  },
  emptyCta: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.accent,
    paddingHorizontal: spacing.xl,
    paddingVertical: spacing.md,
    borderRadius: radii.button,
    gap: spacing.xs,
  },
  emptyCtaText: {
    ...typography.body,
    fontWeight: '600',
    color: colors.bg.primary,
  },
  authContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: spacing.xl,
  },
  authTitle: {
    ...typography.title,
    color: colors.text.primary,
    marginBottom: spacing.xl,
  },
  authButton: {
    backgroundColor: colors.accent,
    paddingHorizontal: spacing['2xl'],
    paddingVertical: spacing.md,
    borderRadius: radii.button,
  },
  authButtonText: {
    ...typography.body,
    fontWeight: '600',
    color: colors.bg.primary,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
});
