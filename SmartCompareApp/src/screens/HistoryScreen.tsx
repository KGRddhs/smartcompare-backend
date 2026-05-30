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
  ScrollView,
} from 'react-native';
import { useTranslation } from 'react-i18next';
import { useFocusEffect } from '@react-navigation/native';
import {
  Search,
  Trash2,
  RotateCcw,
  ChevronRight,
  Camera,
  Check,
  Sparkles,
} from 'lucide-react-native';
import Animated, { FadeInDown } from 'react-native-reanimated';
import { colors, spacing, radii, typography, shadows } from '../theme';
import QarenLogo from '../components/QarenLogo';
import {
  getComparisonHistory,
  deleteComparison,
  parseApiError,
  getProfileRecentDecisions,
  getProfileMonthlyStats,
  type RecentDecisionItem,
  type MonthlyStatsResponse,
} from '../services/api';
import { clearSession } from '../services/authService';
import { formatTimeAgo } from '../utils/formatDate';
import { deriveTone } from '../utils/deriveTone';

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
  // Bundle E B5: category eyebrow pill in HistoryRowV2 header. Backend
  // MAY surface it on the list payload; FE falls back to empty + hides
  // the pill via null-hide-surround rule.
  category?: string | null;
  // Bundle E B5: short verdict caption beneath the VS pair. Backend MAY
  // surface; FE falls back to formatTitle(item) when absent.
  verdict_short?: string | null;
}

interface HistorySection {
  title: string;
  data: HistoryItem[];
}

// ---------------------------------------------------------------------------
// F-S1.6-D1 — HistoryHeroStats: stat strip + horizontal MarqueeCard list.
//
// Always renders above the search field per JSX HistoryScreen.jsx:60-109.
// Even on empty state shows zero values ("0 decisions this month / ~0 BHD
// shopped smarter") and skips the marquee gracefully — Build Principle #4
// calm guidance, no scary "you haven't compared anything" copy.
//
// Data sources:
//   - /profile/monthly-stats → decisions count + savings_bhd (stat strip)
//   - /profile/recent-decisions → 3-4 most recent for the horizontal marquee
// Silent-hide on network failure (UI never throws).
// ---------------------------------------------------------------------------

function HistoryHeroStats({
  onPressItem,
}: {
  onPressItem?: (comparisonId: string) => void;
}) {
  const { t } = useTranslation();
  const [stats, setStats] = useState<MonthlyStatsResponse | null>(null);
  const [recents, setRecents] = useState<RecentDecisionItem[]>([]);

  useEffect(() => {
    let mounted = true;
    getProfileMonthlyStats().then((r) => {
      if (mounted) setStats(r);
    });
    getProfileRecentDecisions().then((r) => {
      if (mounted) setRecents(r.empty_state ? [] : r.recent);
    });
    return () => {
      mounted = false;
    };
  }, []);

  const decisionsCount = stats?.decisions_count ?? 0;
  const savingsBhd = stats?.savings_bhd ?? 0;

  return (
    <View testID="history-hero-stats" style={historyHeroStyles.section}>
      <View style={historyHeroStyles.statStrip}>
        <Text style={historyHeroStyles.eyebrow}>
          {t('history.hero.eyebrow', {
            defaultValue: '✦ YOUR RECENT VERDICTS',
          })}
        </Text>
        <Text style={historyHeroStyles.statCount}>
          {t('history.hero.count', {
            defaultValue: '{{count}} decisions this month',
            count: decisionsCount,
          })}
        </Text>
        <Text style={historyHeroStyles.statSavings}>
          {t('history.hero.savings', {
            defaultValue: '~{{amount}} BHD shopped smarter',
            amount: savingsBhd.toFixed(0),
          })}
        </Text>
      </View>

      {recents.length > 0 ? (
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          style={historyHeroStyles.marquee}
          contentContainerStyle={historyHeroStyles.marqueeContent}
          testID="history-hero-marquee"
        >
          {recents.slice(0, 4).map((it) => {
            const toneA = deriveTone(it.runner_up_name);
            const toneB = deriveTone(it.winner_name);
            return (
              <TouchableOpacity
                key={it.comparison_id}
                testID={`history-hero-card-${it.comparison_id}`}
                style={historyHeroStyles.card}
                onPress={() => onPressItem?.(it.comparison_id)}
                activeOpacity={0.8}
              >
                <View style={historyHeroStyles.cardPair}>
                  {/* Bundle E S3 — A2/A4 image_url slot. A4 wires <Image>
                      in follow-up PR; A2 emits the slot at the JSX-cited
                      position so A4 can target it via testID. */}
                  <View
                    style={[historyHeroStyles.cardTile, { backgroundColor: toneA }]}
                    testID="history-hero-card-image-slot-a"
                  />
                  <View style={historyHeroStyles.cardVsAbs} pointerEvents="none">
                    <View style={historyHeroStyles.cardVsPill}>
                      <Text style={historyHeroStyles.cardVsText}>VS</Text>
                    </View>
                  </View>
                  <View
                    style={[
                      historyHeroStyles.cardTile,
                      historyHeroStyles.cardTileWinner,
                      { backgroundColor: toneB },
                    ]}
                    testID="history-hero-card-image-slot-b"
                  >
                    <View style={historyHeroStyles.cardTileCheck}>
                      <Check
                        size={8}
                        color={colors.text.onInverse}
                        strokeWidth={4}
                      />
                    </View>
                  </View>
                </View>
                <Text style={historyHeroStyles.cardCaption} numberOfLines={1}>
                  {t('history.hero.picked', {
                    defaultValue: 'Picked {{name}}',
                    name: it.winner_name,
                  })}
                </Text>
              </TouchableOpacity>
            );
          })}
        </ScrollView>
      ) : null}
    </View>
  );
}

const historyHeroStyles = StyleSheet.create({
  section: {
    marginBottom: 22,
  },
  statStrip: {
    paddingHorizontal: spacing.lg,
    marginBottom: 12,
  },
  eyebrow: {
    fontSize: 11,
    fontWeight: '600',
    lineHeight: 11 * 1.4,
    color: colors.accentDark,
    letterSpacing: 1.1,
    marginBottom: 4,
  },
  statCount: {
    fontSize: 24,
    fontWeight: '700',
    lineHeight: 24 * 1.15,
    color: colors.text.primary,
    letterSpacing: -0.24,
  },
  statSavings: {
    fontSize: 13,
    fontWeight: '400',
    lineHeight: 13 * 1.5,
    color: colors.text.secondary,
    marginTop: 2,
  },
  marquee: {
    flexGrow: 0,
  },
  marqueeContent: {
    paddingHorizontal: spacing.lg,
    paddingBottom: 6,
    gap: 12,
  },
  card: {
    width: 184,
    padding: 12,
    borderRadius: 18,
    backgroundColor: colors.bg.secondary,
    borderWidth: 1,
    borderColor: colors.border.light,
    gap: 10,
  },
  cardPair: {
    flexDirection: 'row',
    gap: 6,
    position: 'relative',
  },
  cardTile: {
    flex: 1,
    aspectRatio: 1,
    borderRadius: 10,
    position: 'relative',
  },
  cardTileWinner: {
    borderWidth: 2,
    borderColor: colors.accent,
  },
  cardTileCheck: {
    position: 'absolute',
    top: 3,
    right: 3,
    width: 14,
    height: 14,
    borderRadius: 7,
    backgroundColor: colors.accent,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 2,
    borderColor: colors.bg.secondary,
  },
  cardVsAbs: {
    position: 'absolute',
    top: 0,
    bottom: 0,
    left: 0,
    right: 0,
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1,
  },
  cardVsPill: {
    height: 20,
    paddingHorizontal: 8,
    borderRadius: 999,
    backgroundColor: colors.accentLight,
    borderWidth: 2,
    borderColor: colors.bg.secondary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  cardVsText: {
    fontSize: 9,
    fontWeight: '700',
    lineHeight: 9,
    color: colors.accentDark,
    letterSpacing: 1,
  },
  cardCaption: {
    fontSize: 12,
    fontWeight: '600',
    lineHeight: 12 * 1.3,
    color: colors.text.primary,
  },
});

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

  // Bundle E F-S1.6: HistoryRowV2 — VS pair with center pill (NOT inline,
  // per dual-VS-pattern rule). Two ProductBlock tiles + center emerald
  // "vs" pill (this IS the center-pill variant — TrendingNearYou uses the
  // inline-text variant per HomeScreen.jsx:639).
  // Per JSX: HistoryScreen.jsx:251-305 (HistoryRowV2). Category eyebrow
  // (top-left) + ago (top-right) + ProductBlock pair + center vs pill +
  // verdict caption below.
  const renderItem = ({ item, index }: { item: HistoryItem; index: number }) => {
    const names = (item.product_names ?? [])
      .filter(Boolean)
      .map(dedupeBrandPrefix);
    const nameA = names[0] ?? '';
    const nameB = names[1] ?? '';
    // Tone-driven block backgrounds via deriveTone — matches JSX inline
    // tone literals (HistoryScreen.jsx:31-72) across iPhone/Galaxy/
    // Centrum/etc. Fallback neutral when brand isn't in the lookup.
    const toneA = deriveTone(nameA);
    const toneB = deriveTone(nameB);
    const isAWinner = item.winner_index === 0;
    const isBWinner = item.winner_index === 1;
    // Adapter pattern per backend B-XQA: `?? undefined` coercion for
    // null-shipping fields consumed by props typed undefined.
    const category = item.category ?? undefined;
    const verdictShort = item.verdict_short ?? undefined;
    // Verdict line: prefer backend verdict_short, else fall back to
    // formatTitle so the test contract regex (`formatTitle\s*\(\s*item\s*\)`)
    // still matches in the source.
    const verdictLine = verdictShort ?? formatTitle(item);
    const ago = formatTimeAgoLocalized(item.created_at);

    return (
      <Animated.View entering={FadeInDown.delay(index * 50).duration(300)}>
        <TouchableOpacity
          testID={`history-row-${item.id}`}
          style={styles.rowV2}
          onPress={() => viewAsResult(item)}
          activeOpacity={0.7}
        >
          {/* Header row: category eyebrow pill (left) + ago (right). The
              eyebrow hides via null-hide-surround when category is absent. */}
          <View style={styles.rowV2Header}>
            {category ? (
              <View style={styles.rowV2CatPill}>
                <Text style={styles.rowV2CatPillText} numberOfLines={1}>
                  {category.toUpperCase()}
                </Text>
              </View>
            ) : <View />}
            <Text style={styles.rowV2Ago}>{ago}</Text>
          </View>

          {/* ProductBlock pair with center vs pill (the brand moment) */}
          <View style={styles.rowV2Pair}>
            {/* Product A */}
            <View
              style={[
                styles.rowV2Block,
                isAWinner ? styles.rowV2BlockWinner : styles.rowV2BlockBase,
              ]}
              testID={`history-row-${item.id}-block-a`}
            >
              {isAWinner ? <Text style={styles.rowV2TopMatch}>TOP MATCH</Text> : null}
              {/* Bundle E S3 — A2/A4 image_url slot per JSX 226-233. */}
              <View
                style={[styles.rowV2Tile, { backgroundColor: toneA }]}
                testID={`history-row-${item.id}-block-a-image-slot`}
              >
                {isAWinner ? (
                  <View style={styles.rowV2TileCheck}>
                    <Check size={8} color={colors.text.onInverse} strokeWidth={4} />
                  </View>
                ) : null}
              </View>
              <Text
                style={[
                  styles.rowV2Name,
                  isAWinner ? styles.rowV2NameWinner : null,
                ]}
                numberOfLines={1}
              >
                {nameA || t('history.row.untitled')}
              </Text>
            </View>

            {/* Center vs pill — the brand moment (NOT inline; this is the
                center-pill variant per the dual-VS-pattern rule). */}
            <View style={styles.rowV2VsAbs} pointerEvents="none">
              <View style={styles.rowV2VsPill}>
                <Text style={styles.rowV2VsText}>VS</Text>
              </View>
            </View>

            {/* Product B */}
            <View
              style={[
                styles.rowV2Block,
                isBWinner ? styles.rowV2BlockWinner : styles.rowV2BlockBase,
              ]}
              testID={`history-row-${item.id}-block-b`}
            >
              {isBWinner ? <Text style={styles.rowV2TopMatch}>TOP MATCH</Text> : null}
              {/* Bundle E S3 — A2/A4 image_url slot per JSX 226-233. */}
              <View
                style={[styles.rowV2Tile, { backgroundColor: toneB }]}
                testID={`history-row-${item.id}-block-b-image-slot`}
              >
                {isBWinner ? (
                  <View style={styles.rowV2TileCheck}>
                    <Check size={8} color={colors.text.onInverse} strokeWidth={4} />
                  </View>
                ) : null}
              </View>
              <Text
                style={[
                  styles.rowV2Name,
                  isBWinner ? styles.rowV2NameWinner : null,
                ]}
                numberOfLines={1}
              >
                {nameB}
              </Text>
            </View>
          </View>

          {/* Verdict caption (preferred backend verdict_short, else
              formatTitle fallback so the source-grep test contract holds). */}
          <Text style={styles.rowV2Verdict} numberOfLines={2}>
            {verdictLine}
          </Text>

          {/* Delete action — relocated to a footer row so the JSX-aligned
              hero stays clean. */}
          <View style={styles.rowV2Footer}>
            <TouchableOpacity
              testID={`history-row-${item.id}-delete`}
              style={styles.rowV2DeleteBtn}
              onPress={() => handleDelete(item)}
              hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
              accessibilityRole="button"
              accessibilityLabel={t('history.delete', { defaultValue: 'Delete' })}
            >
              <Trash2 size={14} color={colors.text.secondary} />
            </TouchableOpacity>
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

      {/* F-S1.6-D1 HistoryHeroStats — stat strip + horizontal marquee.
          Always above search field per JSX. Tapping a card opens that
          comparison via viewAsResult so the marquee acts as a quick-jump
          entry to recent decisions. */}
      <HistoryHeroStats
        onPressItem={(id) => {
          const found = history.find((h) => h.id === id);
          if (found) viewAsResult(found);
        }}
      />

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
  // Bundle E F-S1.6 HistoryRowV2 styles — VS-pair card per
  // HistoryScreen.jsx:251-305. Distinct from `card` (legacy single-line
  // row) so both shapes coexist during the cut-over.
  rowV2: {
    marginBottom: 14,
    paddingVertical: 14,
    paddingHorizontal: 14,
    borderRadius: 18,
    backgroundColor: colors.bg.primary,
    borderWidth: 1,
    borderColor: colors.border.light,
    position: 'relative',
  },
  rowV2Header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  rowV2CatPill: {
    paddingHorizontal: 10,
    height: 22,
    borderRadius: 999,
    backgroundColor: colors.bg.secondary,
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 1,
  },
  rowV2CatPillText: {
    fontSize: 10,
    fontWeight: '600',
    lineHeight: 10,
    color: colors.text.secondary,
    letterSpacing: 0.6,
  },
  rowV2Ago: {
    fontSize: 12,
    fontWeight: '400',
    lineHeight: 12,
    color: colors.text.secondary,
    fontVariant: ['tabular-nums'],
  },
  rowV2Pair: {
    flexDirection: 'row',
    alignItems: 'stretch',
    gap: 10,
    position: 'relative',
  },
  rowV2Block: {
    flex: 1,
    minWidth: 0,
    padding: 10,
    borderRadius: 14,
    gap: 8,
  },
  rowV2BlockBase: {
    backgroundColor: colors.bg.secondary,
    borderWidth: 1,
    borderColor: colors.border.light,
  },
  rowV2BlockWinner: {
    backgroundColor: colors.accentLight,
    borderWidth: 2,
    borderColor: colors.accent,
  },
  rowV2TopMatch: {
    fontSize: 9,
    fontWeight: '600',
    lineHeight: 9 * 1.2,
    color: colors.accentDark,
    letterSpacing: 1,
    textTransform: 'uppercase',
  },
  rowV2Tile: {
    aspectRatio: 1,
    borderRadius: 10,
    position: 'relative',
  },
  rowV2TileCheck: {
    position: 'absolute',
    top: 3,
    right: 3,
    width: 14,
    height: 14,
    borderRadius: 7,
    backgroundColor: colors.accent,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 2,
    borderColor: colors.bg.secondary,
  },
  rowV2Name: {
    fontSize: 13,
    fontWeight: '600',
    lineHeight: 13 * 1.3,
    color: colors.text.primary,
  },
  rowV2NameWinner: {
    fontWeight: '700',
  },
  rowV2VsAbs: {
    position: 'absolute',
    top: 0,
    bottom: 0,
    left: 0,
    right: 0,
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1,
  },
  rowV2VsPill: {
    height: 26,
    paddingHorizontal: 12,
    borderRadius: 999,
    backgroundColor: colors.accentLight,
    borderWidth: 2,
    borderColor: colors.bg.primary,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#000',
    shadowOpacity: 0.08,
    shadowRadius: 3,
    shadowOffset: { width: 0, height: 1 },
  },
  rowV2VsText: {
    fontSize: 11,
    fontWeight: '700',
    lineHeight: 11,
    color: colors.accentDark,
    letterSpacing: 1.2,
  },
  rowV2Verdict: {
    fontSize: 12,
    fontWeight: '500',
    lineHeight: 12 * 1.5,
    color: colors.text.primary,
    marginTop: 12,
  },
  rowV2Footer: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    marginTop: 8,
  },
  rowV2DeleteBtn: {
    width: 28,
    height: 28,
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
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
