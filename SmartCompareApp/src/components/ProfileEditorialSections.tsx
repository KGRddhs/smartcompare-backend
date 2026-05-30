/**
 * Bundle E F-S1.5f — ProfileScreen editorial sections (always-render).
 *
 * Three sections rendered above the FlatSettings card:
 *   1. RecentDecisionsRow  — horizontal scroll of last 3 mini-vs cards;
 *      empty-state renders ONE invitational card "Your first decision
 *      will live here" routing to Home tab.
 *      (Backend: GET /api/v1/profile/recent-decisions)
 *   2. PrioritiesInline    — ALWAYS 3 slots. Picked priorities use real
 *      bars; unpicked slots show a soft gray placeholder + "+" + "Pick
 *      another priority" caption, all tapping into the EditPreferences
 *      flow via onTunePress.
 *      (Backend: GET /api/v1/profile/priorities-weighted)
 *   3. MonthStrip          — ALWAYS 3 tiles (decisions / BHD saved /
 *      bonus credits). Empty data renders literal "0 / 0 BHD / +0" so
 *      the JSX brand moment survives a first-visit user.
 *      (Backend: GET /api/v1/profile/monthly-stats)
 *
 * F-S1.5f flips the previous "silently hide on empty / threshold-miss /
 * network failure" doctrine to "always render with invitational empty
 * states." Build Principle #4 still applies — no scary copy on the
 * network-failure path; we fall back to the same empty-state surface.
 *
 * Source-of-truth visual: docs/claude-design-handoff/ui_kits/mobile/ProfileScreen.jsx
 * v5 (editorial-rich variant).
 */

import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  ScrollView,
  StyleSheet,
} from 'react-native';
import { useTranslation } from 'react-i18next';
import { Check, Plus } from 'lucide-react-native';
import { colors, spacing, radii, typography } from '../theme';
import {
  getProfileRecentDecisions,
  getProfileMonthlyStats,
  getProfilePrioritiesWeighted,
  type RecentDecisionItem,
  type MonthlyStatsResponse,
  type WeightedPriority,
} from '../services/api';
import { deriveTone } from '../utils/deriveTone';

// ---------------------------------------------------------------------------
// 1. RecentDecisionsRow
// ---------------------------------------------------------------------------

interface RecentDecisionsRowProps {
  onSeeAll?: () => void;
  onItemPress?: (comparisonId: string) => void;
  // F-S1.5f: invoked when the user taps the empty-state invitational card.
  // ProfileScreen wires this to a Home-tab navigation so the first
  // decision lands directly in the compare surface.
  onEmptyCompareTap?: () => void;
}

function timeAgo(iso: string, t: (k: string) => string): string {
  try {
    const created = new Date(iso).getTime();
    const diff = Date.now() - created;
    const mins = Math.floor(diff / 60000);
    if (mins < 60) return t('profile.recent.justNow');
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h`;
    const days = Math.floor(hrs / 24);
    if (days === 1) return t('profile.recent.yesterday');
    if (days < 7) return `${days}d`;
    return new Date(iso).toLocaleDateString();
  } catch {
    return '';
  }
}

function MiniVsCard({
  item,
  onPress,
  t,
}: {
  item: RecentDecisionItem;
  onPress?: () => void;
  t: (k: string) => string;
}) {
  // Per JSX (ProfileScreen.jsx:122-130): each MiniProduct tile uses a
  // brand-derived tone background. Backend ships winner_name + runner_up_name;
  // deriveTone() maps each to its canonical hex per the JSX inline literals.
  // Winner gets a 2px emerald outline + check overlay (top-right).
  const winnerTone = deriveTone(item.winner_name);
  const runnerUpTone = deriveTone(item.runner_up_name);

  return (
    <TouchableOpacity
      testID="profile-recent-card"
      style={styles.miniCard}
      onPress={onPress}
      activeOpacity={0.7}
    >
      <View style={styles.miniRow}>
        <View style={[styles.miniTile, { backgroundColor: runnerUpTone }]} />
        <View style={styles.miniVsPill}>
          <Text style={styles.miniVsText}>{t('profile.recent.vs')}</Text>
        </View>
        <View
          style={[
            styles.miniTile,
            styles.miniTileWinner,
            { backgroundColor: winnerTone },
          ]}
        >
          <View style={styles.miniTileCheck}>
            <Check size={7} color={colors.text.onInverse} strokeWidth={4} />
          </View>
        </View>
      </View>
      <Text style={styles.miniMeta} numberOfLines={1}>
        {item.winner_name} · {timeAgo(item.created_at, t)}
      </Text>
    </TouchableOpacity>
  );
}

export function RecentDecisionsRow({
  onSeeAll,
  onItemPress,
  onEmptyCompareTap,
}: RecentDecisionsRowProps) {
  const { t } = useTranslation();
  const [items, setItems] = useState<RecentDecisionItem[] | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let mounted = true;
    getProfileRecentDecisions()
      .then((r) => {
        if (!mounted) return;
        setItems(r.empty_state ? [] : r.recent);
        setLoaded(true);
      })
      .catch(() => {
        if (!mounted) return;
        // F-S1.5f: network failure routes through the same empty-state
        // surface as `empty_state=true`. No scary copy, no error banner.
        setItems([]);
        setLoaded(true);
      });
    return () => {
      mounted = false;
    };
  }, []);

  // Don't render the section until the first response/error lands —
  // prevents a flash of empty-state on logged-in users with data.
  if (!loaded) return null;

  const isEmpty = !items || items.length === 0;

  return (
    <View testID="profile-recent-decisions" style={styles.section}>
      <View style={styles.sectionHeader}>
        <Text style={styles.sectionEyebrow}>
          {t('profile.recent.title')}
        </Text>
        {/* See-all is only useful when there's a populated history. */}
        {onSeeAll && !isEmpty && (
          <TouchableOpacity onPress={onSeeAll} testID="profile-recent-see-all">
            <Text style={styles.seeAllLink}>{t('profile.recent.seeAll')}</Text>
          </TouchableOpacity>
        )}
      </View>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.miniScroll}
      >
        {isEmpty ? (
          <TouchableOpacity
            testID="profile-recent-empty-card"
            style={[styles.miniCard, styles.miniEmptyCard]}
            onPress={onEmptyCompareTap}
            activeOpacity={onEmptyCompareTap ? 0.7 : 1}
            disabled={!onEmptyCompareTap}
            accessibilityRole="button"
            accessibilityLabel={`${t('profile.recent.empty.title')} ${t(
              'profile.recent.empty.caption',
            )}`}
          >
            <Text style={styles.miniEmptyTitle} numberOfLines={2}>
              {t('profile.recent.empty.title')}
            </Text>
            <Text style={styles.miniEmptyCaption} numberOfLines={1}>
              {t('profile.recent.empty.caption')}
            </Text>
          </TouchableOpacity>
        ) : (
          items!.map((it) => (
            <MiniVsCard
              key={it.comparison_id}
              item={it}
              t={t}
              onPress={onItemPress ? () => onItemPress(it.comparison_id) : undefined}
            />
          ))
        )}
      </ScrollView>
    </View>
  );
}

// ---------------------------------------------------------------------------
// 2. PrioritiesInline
// ---------------------------------------------------------------------------

interface PrioritiesInlineProps {
  onTunePress?: () => void;
}

// F-S1.5f: Profile editorial doctrine = always show 3 slots so the
// "What shapes your matches" brand moment lands even when the user has
// fewer than 3 picked priorities. JSX ProfileScreen.jsx:164-200 shows 3
// bars; this card honors the structure on first visit too.
const PRIORITY_SLOT_COUNT = 3;

export function PrioritiesInline({ onTunePress }: PrioritiesInlineProps) {
  const { t } = useTranslation();
  const [priorities, setPriorities] = useState<WeightedPriority[] | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let mounted = true;
    getProfilePrioritiesWeighted()
      .then((r) => {
        if (!mounted) return;
        setPriorities(r.empty_state ? [] : r.priorities);
        setLoaded(true);
      })
      .catch(() => {
        if (!mounted) return;
        setPriorities([]);
        setLoaded(true);
      });
    return () => {
      mounted = false;
    };
  }, []);

  // Same "wait for first response" guard as RecentDecisionsRow — prevents
  // a flash of 3 placeholders before real data lands.
  if (!loaded) return null;

  // B3 (Path A): humanize fallback for any backend label_key not in i18n
  // (cohort-derived priorities like `trust_known_brands` may not have a
  // dedicated translation). Default: "snake_case" → "Snake case".
  const humanize = (raw: string): string => {
    if (!raw) return raw;
    return raw
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (c) => c.toUpperCase());
  };
  const resolveLabel = (label_key: string, key: string): string => {
    const resolved = t(label_key);
    if (resolved && resolved !== label_key) return resolved;
    return humanize(key);
  };

  const filled = priorities ?? [];
  const emptySlots = Math.max(0, PRIORITY_SLOT_COUNT - filled.length);

  return (
    <View testID="profile-priorities-inline" style={styles.prioritiesCard}>
      <Text style={styles.prioritiesTitle}>
        {t('profile.priorities.title')}
      </Text>
      <View style={styles.prioritiesList}>
        {filled.slice(0, PRIORITY_SLOT_COUNT).map((p) => (
          <View key={p.key} style={styles.prioritiesRow}>
            <Text style={styles.prioritiesLabel} numberOfLines={1}>
              {resolveLabel(p.label_key, p.key)}
            </Text>
            <View style={styles.prioritiesBarTrack}>
              <View
                style={[
                  styles.prioritiesBarFill,
                  { width: `${Math.max(0, Math.min(100, p.weight))}%` },
                ]}
              />
            </View>
            <Text style={styles.prioritiesPercent}>{p.weight}%</Text>
          </View>
        ))}
        {Array.from({ length: emptySlots }, (_, i) => (
          <TouchableOpacity
            key={`empty-${i}`}
            testID={`profile-priorities-empty-${i}`}
            style={styles.prioritiesEmptyRow}
            onPress={onTunePress}
            disabled={!onTunePress}
            activeOpacity={onTunePress ? 0.6 : 1}
            accessibilityRole="button"
            accessibilityLabel={t('profile.priorities.pickAnother')}
          >
            <View style={styles.prioritiesEmptyIconWrap}>
              <Plus size={14} color={colors.text.placeholder} strokeWidth={2.5} />
            </View>
            <Text style={styles.prioritiesEmptyLabel} numberOfLines={1}>
              {t('profile.priorities.pickAnother')}
            </Text>
          </TouchableOpacity>
        ))}
      </View>
      {onTunePress && (
        <TouchableOpacity
          testID="profile-priorities-tune"
          style={styles.prioritiesCta}
          onPress={onTunePress}
        >
          <Text style={styles.prioritiesCtaText}>
            {t('profile.priorities.tuneCta')}
          </Text>
        </TouchableOpacity>
      )}
    </View>
  );
}

// ---------------------------------------------------------------------------
// 3. MonthStrip
// ---------------------------------------------------------------------------

export function MonthStrip() {
  const { t } = useTranslation();
  const [stats, setStats] = useState<MonthlyStatsResponse | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let mounted = true;
    getProfileMonthlyStats()
      .then((r) => {
        if (!mounted) return;
        setStats(r);
        setLoaded(true);
      })
      .catch(() => {
        if (!mounted) return;
        setStats(null);
        setLoaded(true);
      });
    return () => {
      mounted = false;
    };
  }, []);

  // F-S1.5f: Always show the strip after first load so the JSX brand
  // moment (3 tiles below the priorities card) lands on first visit.
  // Wait for the initial fetch to settle to avoid a flash of zeros for
  // users who actually have data.
  if (!loaded) return null;

  // Zero-state when threshold not met OR data missing (network failure).
  // JSX literal: "0 / 0 BHD / +0" — literal zeros, NEVER hide.
  const decisionsCount = stats?.decisions_count ?? 0;
  const savingsBhd = stats?.savings_bhd ?? 0;
  const bonusCredits = stats?.bonus_credits_this_month ?? 0;

  return (
    <View testID="profile-month-strip" style={styles.monthStrip}>
      <View style={styles.statTile} testID="profile-month-stat-decisions">
        <Text style={styles.statNumber}>{decisionsCount}</Text>
        <Text style={styles.statLabel}>{t('profile.month.decisions')}</Text>
      </View>
      <View style={styles.statTile} testID="profile-month-stat-savings">
        <Text style={[styles.statNumber, styles.statNumberAccent]}>
          {savingsBhd.toFixed(0)}
        </Text>
        <Text style={styles.statLabel}>{t('profile.month.savings')}</Text>
      </View>
      <View style={styles.statTile} testID="profile-month-stat-bonus">
        <Text style={styles.statNumber}>
          +{bonusCredits}
        </Text>
        <Text style={styles.statLabel}>{t('profile.month.bonus')}</Text>
      </View>
    </View>
  );
}

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const styles = StyleSheet.create({
  section: {
    marginBottom: spacing.xl,
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'baseline',
    justifyContent: 'space-between',
    paddingHorizontal: spacing.lg,
    marginBottom: spacing.sm,
  },
  sectionEyebrow: {
    ...typography.caption,
    fontWeight: '600',
    color: colors.text.secondary,
    textTransform: 'uppercase',
    letterSpacing: 1.1,
  },
  seeAllLink: {
    ...typography.caption,
    fontWeight: '500',
    color: colors.accent,
  },
  miniScroll: {
    paddingHorizontal: spacing.lg,
    gap: spacing.sm,
  },
  miniCard: {
    width: 168,
    padding: spacing.md,
    borderRadius: radii.card,
    backgroundColor: colors.bg.secondary,
    borderWidth: 1,
    borderColor: colors.border.light,
    gap: spacing.sm,
    marginEnd: spacing.sm,
  },
  miniRow: {
    flexDirection: 'row',
    alignItems: 'stretch',
    gap: 6,
    position: 'relative',
  },
  miniTile: {
    flex: 1,
    aspectRatio: 1,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
    position: 'relative',
  },
  miniTileMuted: {
    backgroundColor: '#E8E9ED',
  },
  miniTileWinner: {
    // backgroundColor overridden inline via deriveTone() — keep the
    // border-only spec here so winner gets the emerald outline + check
    // overlay no matter which brand-tone is applied.
    borderWidth: 2,
    borderColor: colors.accent,
  },
  miniTileGlyph: {
    color: 'rgba(0,0,0,0.18)',
    fontSize: 14,
  },
  // Bundle E winner check overlay (per ProfileScreen.jsx:105-117 MiniProduct
  // winner adornment — 12px emerald circle with white check, top-right of tile).
  miniTileCheck: {
    position: 'absolute',
    top: 3,
    right: 3,
    width: 12,
    height: 12,
    borderRadius: 6,
    backgroundColor: colors.accent,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1.5,
    borderColor: colors.bg.secondary,
  },
  miniVsPill: {
    position: 'absolute',
    top: '50%',
    left: '50%',
    transform: [{ translateX: -12 }, { translateY: -9 }],
    height: 18,
    paddingHorizontal: 6,
    borderRadius: 999,
    backgroundColor: colors.accentLight,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 2,
    borderColor: colors.bg.secondary,
    zIndex: 1,
  },
  miniVsText: {
    ...typography.small,
    fontWeight: '700',
    fontSize: 8,
    color: colors.accentDark,
    letterSpacing: 0.8,
    textTransform: 'uppercase',
  },
  miniMeta: {
    ...typography.small,
    color: colors.text.secondary,
  },
  // F-S1.5f empty-state card — same outer shape as MiniVsCard so the
  // marquee shelf reads consistently whether populated or empty. Body
  // is invitational: title + caption stacked, no vs/winner adornment.
  miniEmptyCard: {
    justifyContent: 'center',
    gap: spacing.xs,
    borderStyle: 'dashed',
    borderColor: colors.border.medium,
  },
  miniEmptyTitle: {
    ...typography.caption,
    fontWeight: '600',
    color: colors.text.primary,
  },
  miniEmptyCaption: {
    ...typography.small,
    color: colors.accentDark,
  },
  // Priorities card
  prioritiesCard: {
    marginHorizontal: spacing.lg,
    marginBottom: spacing.xl,
    padding: spacing.lg,
    borderRadius: radii.card,
    backgroundColor: colors.bg.secondary,
    borderWidth: 1,
    borderColor: colors.border.light,
  },
  prioritiesTitle: {
    ...typography.title,
    fontSize: 16,
    color: colors.text.primary,
    marginBottom: spacing.md,
  },
  prioritiesList: {
    gap: spacing.sm,
  },
  prioritiesRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
  },
  // F-S1.5f placeholder row — soft gray "+" + caption "Pick another
  // priority", tappable to EditPreferences. Keeps the 3-slot rhythm so
  // the card never collapses to fewer rows than JSX:178-189 promises.
  prioritiesEmptyRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    minHeight: 22,
  },
  prioritiesEmptyIconWrap: {
    width: 22,
    height: 22,
    borderRadius: 11,
    backgroundColor: colors.bg.primary,
    borderWidth: 1,
    borderStyle: 'dashed',
    borderColor: colors.border.medium,
    alignItems: 'center',
    justifyContent: 'center',
  },
  prioritiesEmptyLabel: {
    flex: 1,
    ...typography.caption,
    fontWeight: '500',
    color: colors.text.placeholder,
  },
  prioritiesLabel: {
    width: 88,
    ...typography.caption,
    fontWeight: '500',
    color: colors.text.primary,
  },
  prioritiesBarTrack: {
    flex: 1,
    height: 6,
    borderRadius: 999,
    backgroundColor: colors.border.light,
    overflow: 'hidden',
  },
  prioritiesBarFill: {
    height: '100%',
    backgroundColor: colors.accent,
  },
  prioritiesPercent: {
    width: 36,
    textAlign: 'right',
    ...typography.small,
    color: colors.text.secondary,
  },
  prioritiesCta: {
    marginTop: spacing.md,
    width: '100%',
    height: 44,
    borderRadius: 22,
    backgroundColor: colors.text.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  prioritiesCtaText: {
    ...typography.body,
    fontWeight: '600',
    color: colors.bg.primary,
  },
  // Month strip
  monthStrip: {
    flexDirection: 'row',
    gap: spacing.sm,
    marginHorizontal: spacing.lg,
    marginBottom: spacing.xl,
  },
  statTile: {
    flex: 1,
    padding: spacing.md,
    borderRadius: radii.card,
    backgroundColor: colors.bg.secondary,
    borderWidth: 1,
    borderColor: colors.border.light,
  },
  statNumber: {
    ...typography.title,
    fontSize: 22,
    fontWeight: '700',
    color: colors.text.primary,
  },
  statNumberAccent: {
    color: colors.accentDark,
  },
  statLabel: {
    ...typography.small,
    color: colors.text.secondary,
    marginTop: spacing.xs,
  },
});
