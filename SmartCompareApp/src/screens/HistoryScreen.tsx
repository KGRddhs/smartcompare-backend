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
import QarenLogo from '../components/QarenLogo';
import { getComparisonHistory, deleteComparison, parseApiError } from '../services/api';
import { clearSession } from '../services/authService';
import { formatTimeAgo } from '../utils/formatDate';

interface HistoryItem {
  id: string;
  full_response: any;
  query: string;
  input_type: string;
  product_names: string[];
  // Bundle D 2.6.B.4 (Backend commit 0384de3): backend now emits
  // winner_index on the list response so per-row VS cards can outline
  // the winner without fetching the full payload.
  //   0 → outline product_names[0]; 1 → outline product_names[1]; null →
  //   no outline (legacy rows or rows where the pipeline didn't emit it).
  winner_index?: 0 | 1 | null;
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
  const { t, i18n } = useTranslation();
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
        if (__DEV__) console.error('Error loading history:', error);
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

  // Locale-aware relative time via i18n-opus' shared util (Bundle A §6.2).
  // Replaces the inline hardcoded 'en-US' formatter so Arabic users get
  // "منذ 2 يوم" / "الآن" instead of "2d ago" / "<1m ago".
  const formatTimeAgoLocalized = (dateString: string): string =>
    formatTimeAgo(dateString, (i18n.language as 'en' | 'ar') ?? 'en');

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
    // Bucket A bug 1: list endpoint returns summary only — item.full_response
    // is always null. Pass comparison_id so ResultsScreen can fetch the full
    // payload via getComparison(id) on mount.
    navigation.navigate('Results', { comparison_id: item.id });
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
              Alert.alert(t('common.error'), t('history.deleteError'));
            }
          },
        },
      ]
    );
  };

  // B2 (Path A): defensive de-dupe of consecutive duplicate word(s) at the
  // start of a product name. Older comparison rows were saved with shapes
  // where the brand prefix got concatenated twice (e.g. "Apple Apple
  // iPhone 14", "Louis Vuitton Louis Vuitton Mesh Cap", "HealthAid
  // HealthAid Vit D"). Backend doesn't rewrite stored rows; FE collapses
  // visually so the history reads cleanly.
  const dedupeBrandPrefix = (name: string): string => {
    const trimmed = name.trim();
    if (!trimmed) return trimmed;
    // 2-word brand dedupe: "Louis Vuitton Louis Vuitton Mesh Cap" → "Louis Vuitton Mesh Cap"
    const m2 = trimmed.match(/^(\S+\s+\S+)\s+\1\b/i);
    if (m2) return trimmed.slice(m2[1].length + 1).trimStart();
    // 1-word brand dedupe: "Apple Apple iPhone 14" → "Apple iPhone 14"
    const m1 = trimmed.match(/^(\S+)\s+\1\b/i);
    if (m1) return trimmed.slice(m1[1].length + 1).trimStart();
    return trimmed;
  };

  const formatTitle = (item: HistoryItem): string => {
    // Bundle A §5.3 — list endpoint returns `product_names` (summary fields
    // only; full_response is not in the list payload). The legacy
    // `item.full_response?.products` lookup never worked because the list
    // route doesn't hydrate full_response.
    const names = (item.product_names ?? [])
      .filter(Boolean)
      .map(dedupeBrandPrefix);
    if (names.length >= 2) {
      const combined = `${names[0]} vs ${names[1]}`;
      return combined.length > 40 ? combined.slice(0, 39) + '…' : combined;
    }
    const q = item.query?.trim();
    if (q) return q;
    return t('history.row.untitled');
  };

  // Bundle D 2.6.B.4 — render the title as 3 inline spans so the winning
  // product name can be highlighted (emerald + bolder). When winner_index
  // is null or names are unavailable, falls back to the plain formatTitle().
  const renderTitle = (item: HistoryItem) => {
    const names = (item.product_names ?? [])
      .filter(Boolean)
      .map(dedupeBrandPrefix);
    if (names.length < 2 || (item.winner_index !== 0 && item.winner_index !== 1)) {
      return (
        <Text style={styles.cardQuery} numberOfLines={1}>
          {formatTitle(item)}
        </Text>
      );
    }
    const winnerStyle = [styles.cardQuery, styles.cardQueryWinner];
    const loserStyle = styles.cardQuery;
    const aStyle = item.winner_index === 0 ? winnerStyle : loserStyle;
    const bStyle = item.winner_index === 1 ? winnerStyle : loserStyle;
    return (
      <Text style={styles.cardQuery} numberOfLines={1}>
        <Text style={aStyle}>{names[0]}</Text>
        <Text style={styles.cardQueryVs}> {t('profile.recent.vs')} </Text>
        <Text style={bStyle}>{names[1]}</Text>
      </Text>
    );
  };

  const renderItem = ({ item, index }: { item: HistoryItem; index: number }) => {
    return (
      <Animated.View entering={FadeInDown.delay(index * 50).duration(300)}>
        <TouchableOpacity
          style={styles.card}
          onPress={() => viewAsResult(item)}
          activeOpacity={0.7}
        >
          <View style={styles.cardContent}>
            <View style={styles.cardTop}>
              {renderTitle(item)}
              <Text style={styles.cardTime}>{formatTimeAgoLocalized(item.created_at)}</Text>
            </View>
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
        {/* Bundle B/C/D Task 2.10 — brand glyph leading the screen title. */}
        <QarenLogo size={24} />
        <Text style={[styles.headerTitle, styles.headerTitleSpaced]}>
          {t('history.title')}
        </Text>
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
  // Bundle D Claude-Design (option small, Task 2.F.2 screen 4): header
  // alignment tweak — `alignItems: 'baseline'` so the QarenLogo glyph
  // base-aligns with the display-type title (vs. center which had the
  // glyph optically floating above the title cap-height).
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.base,
    paddingBottom: spacing.md,
  },
  headerTitle: {
    ...typography.display,
    color: colors.text.primary,
  },
  // Bundle B/C/D Task 2.10 — RTL-safe spacer between the QarenLogo glyph
  // and the screen-title text.
  headerTitleSpaced: {
    marginStart: spacing.sm,
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
  // Bundle D Claude-Design (option small, Task 2.F.2 screen 4): section
  // header upgraded to eyebrow treatment per design system (smaller text,
  // wider letterSpacing, uppercase, secondary color). Matches the eyebrow
  // pattern Claude-Design uses on the HistoryScreen "Today / Yesterday /
  // This Week / Older" section labels (history.html section anchors).
  sectionHeader: {
    ...typography.eyebrow,
    color: colors.text.secondary,
    marginTop: spacing.lg,
    marginBottom: spacing.sm,
  },
  // Bundle D Claude-Design: row card refresh — bg.secondary fill +
  // border.light hairline outline matches Claude-Design `MarqueeCard`
  // visual treatment. Single change is the hairline border — the
  // existing fill + radius were already tokens-aligned.
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.bg.secondary,
    borderRadius: radii.card,
    borderWidth: 1,
    borderColor: colors.border.light,
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
  // Bundle D 2.6.B.4 — emerald-accented bolder span for the winning product
  // name within the "A vs B" title row. Color signals the pick at a glance
  // without adding a separate badge.
  cardQueryWinner: {
    color: colors.accentDark,
    fontWeight: '700',
  },
  cardQueryVs: {
    color: colors.text.secondary,
    fontWeight: '400',
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
