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
import { ProductImage } from '../components/primitives/ProductImage';
import { DirectionalIcon } from '../components/primitives/DirectionalIcon';
import { localizedCurrency } from '../utils/currencyDisplay';
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
  // Bundle E S3 Hot-Fix Wave 2 (L3 endpoint extension): backend computes
  // these from full_response.products[winner_index].image_url and
  // full_response.products[1 - winner_index].image_url so the list-row
  // render does not need to traverse the full_response JSONB on every
  // row. Optional + nullable — list cache from pre-Wave-2 deploys will
  // still ship without them; the row reader falls back to the
  // full_response traversal in that case.
  winner_image_url?: string | null;
  runner_up_image_url?: string | null;
}

interface HistorySection {
  title: string;
  data: HistoryItem[];
}

// B2 (Path A): defensive de-dupe of consecutive duplicate word(s) at the
// start of a product name. Older comparison rows were saved with shapes
// where the brand prefix got concatenated twice (e.g. "Apple Apple
// iPhone 14", "Louis Vuitton Louis Vuitton Mesh Cap", "HealthAid
// HealthAid Vit D"). Backend doesn't rewrite stored rows; FE collapses
// visually so the history reads cleanly. (M21: hoisted to module level —
// pure, so the memoized HistoryRow and the screen share one instance.)
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

// M21 MB-perf-07 — entrance-stagger cap. The old `index * 50` scaled the
// FadeInDown delay with the row's position INSIDE its section; the
// "Older" section can hold ~44 of the 50 fetched rows, so a row mounted
// by scrolling sat invisible for up to ~2.2s — and SectionList
// virtualization re-mounts rows scrolled out and back in, re-running the
// same delayed entrance. Capping at 6 steps keeps the first-paint
// stagger (the delight it was built for) while bounding any row's
// invisible window to 300ms.
const ROW_STAGGER_STEP_MS = 50;
const ROW_STAGGER_MAX_STEPS = 6;
export const rowEntranceDelayMs = (index: number): number =>
  Math.min(index, ROW_STAGGER_MAX_STEPS) * ROW_STAGGER_STEP_MS;

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

// M21 MB-perf-06 + MB-flows-08: memoized so search keystrokes in the
// parent don't re-render the 4-card marquee (8 remote ProductImages), and
// given `excludeIds` so a just-deleted comparison is pruned instead of
// staying tappable (the hero fetches once on mount and would otherwise
// keep serving the deleted row).
const HistoryHeroStats = React.memo(function HistoryHeroStats({
  onPressItem,
  excludeIds,
}: {
  onPressItem?: (comparisonId: string) => void;
  excludeIds?: ReadonlySet<string>;
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
  const visibleRecents = recents.filter(
    (it) => !excludeIds?.has(it.comparison_id)
  );

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

      {visibleRecents.length > 0 ? (
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          style={historyHeroStyles.marquee}
          contentContainerStyle={historyHeroStyles.marqueeContent}
          testID="history-hero-marquee"
        >
          {visibleRecents.slice(0, 4).map((it) => {
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
                  {/* Bundle E S3 A4 Wave 2 — ProductImage 4-state primitive.
                      RecentDecisionItem may include winner_image_url +
                      runner_up_image_url (forward-compat); placeholder tone
                      falls back to the per-brand toneA / toneB palette. */}
                  <ProductImage
                    testID="history-hero-card-image-slot-a"
                    imageUrl={it.runner_up_image_url}
                    placeholderTone={toneA}
                    aspectRatio={1}
                    borderRadius={radii.button}
                    style={historyHeroStyles.cardTile}
                  />
                  <View style={historyHeroStyles.cardVsAbs} pointerEvents="none">
                    <View style={historyHeroStyles.cardVsPill}>
                      <Text style={historyHeroStyles.cardVsText}>VS</Text>
                    </View>
                  </View>
                  <View style={historyHeroStyles.cardTileWinnerWrap}>
                    <ProductImage
                      testID="history-hero-card-image-slot-b"
                      imageUrl={it.winner_image_url}
                      placeholderTone={toneB}
                      aspectRatio={1}
                      borderRadius={radii.button}
                      style={[historyHeroStyles.cardTile, historyHeroStyles.cardTileWinner]}
                    />
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
});

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
  // Bundle E S3 A4 Wave 2 — wraps ProductImage to host the absolute-
  // positioned winner check chip without violating the primitive's
  // self-contained tile.
  cardTileWinnerWrap: {
    flex: 1,
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

interface HistoryRowProps {
  item: HistoryItem;
  index: number;
  onPress: (item: HistoryItem) => void;
  onDelete: (item: HistoryItem) => void;
}

// ---------------------------------------------------------------------------
// M21 MB-perf-06/07 — HistoryRow, extracted from the screen's inline
// renderItem closure and memoized.
//
// Before: renderItem was an inline arrow on the screen body with ZERO
// memoized components anywhere in the app, so every search keystroke
// (screen-level `setSearchQuery` state) re-rendered EVERY mounted row —
// measured 26 deriveTone-bearing row/hero renders per keystroke at 12
// rows in jest — each row re-deriving tones and re-diffing 2 remote
// ProductImages + SVG check chips. After: React.memo + stable
// `onPress`/`onDelete` callbacks from the screen means a keystroke
// re-renders the screen shell only — 0 row re-renders (pinned by
// HistoryScreen.mobileJank.m21.test.tsx).
//
// Bundle E F-S1.6: HistoryRowV2 — VS pair with center pill (NOT inline,
// per dual-VS-pattern rule). Two ProductBlock tiles + center emerald
// "vs" pill (this IS the center-pill variant — TrendingNearYou uses the
// inline-text variant per HomeScreen.jsx:639).
// Per JSX: HistoryScreen.jsx:251-305 (HistoryRowV2). Category eyebrow
// (top-left) + ago (top-right) + ProductBlock pair + center vs pill +
// verdict caption below.
// ---------------------------------------------------------------------------
const HistoryRow = React.memo(function HistoryRow({
  item,
  index,
  onPress,
  onDelete,
}: HistoryRowProps) {
  const { t, i18n } = useTranslation();

  // Locale-aware relative time via i18n-opus' shared util (Bundle A §6.2).
  const formatTimeAgoLocalized = (dateString: string): string =>
    formatTimeAgo(dateString, (i18n.language as 'en' | 'ar') ?? 'en');

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
  // (Currently unreferenced by the RowV2 layout — kept verbatim, as before
  // the M21 extraction, for the planned title treatment.)
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
  void renderTitle;

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
  // Bundle E S3 Hot-Fix Wave 2 — prefer the top-level
  // winner_image_url + runner_up_image_url fields (L3 endpoint
  // extension, shallow payload), fall back to the full_response
  // traversal for backward-compat with pre-Wave-2 cached list state.
  // Mapping is winner-relative: when winner_index=0, block A is the
  // WINNER tile, so imageUrlA reads winner_image_url; when
  // winner_index=1, the mapping inverts. winner_index can be null
  // (legacy rows where the pipeline didn't emit it) — in that case we
  // fall straight through to the full_response slice.
  const fullResponseProducts =
    (item.full_response && Array.isArray(item.full_response.products))
      ? item.full_response.products
      : [];
  const imageUrlA: string | null = isAWinner
    ? (item.winner_image_url ?? fullResponseProducts[0]?.image_url ?? null)
    : (item.runner_up_image_url ?? fullResponseProducts[0]?.image_url ?? null);
  const imageUrlB: string | null = isBWinner
    ? (item.winner_image_url ?? fullResponseProducts[1]?.image_url ?? null)
    : (item.runner_up_image_url ?? fullResponseProducts[1]?.image_url ?? null);
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
    <Animated.View
      entering={FadeInDown.delay(rowEntranceDelayMs(index)).duration(300)}
    >
      <TouchableOpacity
        testID={`history-row-${item.id}`}
        style={styles.rowV2}
        onPress={() => onPress(item)}
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
            {isAWinner ? (
              <Text style={styles.rowV2TopMatch}>{t('results.topMatch')}</Text>
            ) : null}
            {/* Bundle E S3 A4 Wave 2 — ProductImage primitive per JSX
                HistoryScreen.jsx:226-233. tone background falls through
                as placeholderTone. */}
            <View style={styles.rowV2TileWrap}>
              <ProductImage
                testID={`history-row-${item.id}-block-a-image-slot`}
                imageUrl={imageUrlA}
                placeholderTone={toneA}
                aspectRatio={1}
                borderRadius={radii.button}
                style={styles.rowV2Tile}
              />
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
            {isBWinner ? (
              <Text style={styles.rowV2TopMatch}>{t('results.topMatch')}</Text>
            ) : null}
            {/* Bundle E S3 A4 Wave 2 — ProductImage primitive per JSX
                HistoryScreen.jsx:226-233. */}
            <View style={styles.rowV2TileWrap}>
              <ProductImage
                testID={`history-row-${item.id}-block-b-image-slot`}
                imageUrl={imageUrlB}
                placeholderTone={toneB}
                aspectRatio={1}
                borderRadius={radii.button}
                style={styles.rowV2Tile}
              />
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
            onPress={() => onDelete(item)}
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
});

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
  // M21 MB-flows-08 — ids deleted THIS session, so the mount-once hero
  // marquee prunes them instead of keeping a dead (now 404) comparison
  // tappable.
  const [deletedRecentIds, setDeletedRecentIds] = useState<ReadonlySet<string>>(
    new Set()
  );

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

  const formatPrice = (product: any): string => {
    if (!product || product.price === null || product.price === undefined) return 'N/A';
    // MB-i18n-rtl-02 — currency label follows the app language, matching
    // the hero copy ("د.ب" in AR) instead of mixing Latin ISO into Arabic.
    if (typeof product.price === 'object') {
      if (product.price.amount === null || product.price.amount === undefined) return 'N/A';
      return `${product.price.amount.toFixed(2)} ${localizedCurrency(product.price.currency || 'BHD', t)}`;
    }
    return `${(product.price as number).toFixed(2)} ${localizedCurrency('BHD', t)}`;
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

  // M21 MB-perf-06 — stable via useCallback so the memoized HistoryRow's
  // props don't churn on every screen re-render (each search keystroke).
  const viewAsResult = useCallback((item: HistoryItem) => {
    // Bucket A bug 1: list endpoint returns summary only — item.full_response
    // is always null. Pass comparison_id so ResultsScreen can fetch the full
    // payload via getComparison(id) on mount.
    navigation.navigate('Results', { comparison_id: item.id });
  }, [navigation]);

  // M21 MB-flows-08 — the hero marquee is fed by /profile/recent-decisions,
  // which can disagree with the separately fetched (and search-filtered)
  // history page. The old handler resolved the id against `history` and
  // silently dropped the tap on a miss; viewAsResult only ever needed the
  // id, so navigate with it directly.
  const openRecentDecision = useCallback((comparisonId: string) => {
    navigation.navigate('Results', { comparison_id: comparisonId });
  }, [navigation]);

  const handleDelete = useCallback((item: HistoryItem) => {
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
              // M21 MB-flows-08 — prune the mount-once hero marquee too.
              setDeletedRecentIds((prev) => {
                const next = new Set(prev);
                next.add(item.id);
                return next;
              });
            } catch {
              Alert.alert(t('common.error'), t('history.deleteError'));
            }
          },
        },
      ]
    );
  }, [t]);

  // M21 MB-perf-06/07 — renderItem returns the memoized HistoryRow with
  // stable callbacks; the row body (tones, images, title derivation)
  // lives in HistoryRow at module level so screen-level state churn
  // (search keystrokes) no longer re-renders mounted rows.
  const renderItem = useCallback(
    ({ item, index }: { item: HistoryItem; index: number }) => (
      <HistoryRow
        item={item}
        index={index}
        onPress={viewAsResult}
        onDelete={handleDelete}
      />
    ),
    [viewAsResult, handleDelete]
  );


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
        <DirectionalIcon>
          <ChevronRight size={16} color={colors.bg.primary} />
        </DirectionalIcon>
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
          comparison as a quick-jump entry to recent decisions.
          M21 MB-flows-08: navigate with the id DIRECTLY — the old
          `history.find(...)` gate silently no-op'd whenever the two
          endpoints disagreed (recent decision beyond the 50-row page, an
          active search filter, or a just-deleted row). deletedRecentIds
          prunes deleted comparisons from the mount-once marquee. */}
      <HistoryHeroStats
        onPressItem={openRecentDecision}
        excludeIds={deletedRecentIds}
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
  // Bundle E S3 A4 Wave 2 — wraps ProductImage to host the absolute-
  // positioned winner check chip without violating the primitive's
  // self-contained tile.
  rowV2TileWrap: {
    position: 'relative',
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
