/**
 * Bundle D 2.F.2 Screen 3 — ProfileScreen editorial sections.
 *
 * Three optional sections rendered above the existing settings cards:
 *   1. RecentDecisionsRow  — horizontal scroll of last 3 mini-vs cards
 *      (Backend: GET /api/v1/profile/recent-decisions)
 *   2. PrioritiesInline    — 3 weighted priority bars + "Tune" CTA
 *      (Backend: GET /api/v1/profile/priorities-weighted)
 *   3. MonthStrip          — 3-stat row (decisions / savings / bonus credits)
 *      (Backend: GET /api/v1/profile/monthly-stats — hidden unless threshold_met)
 *
 * Each section silently hides on `empty_state=true` / threshold-miss / network
 * failure. Build Principle #4 — never frame the app as scary.
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
import { colors, spacing, radii, typography } from '../theme';
import {
  getProfileRecentDecisions,
  getProfileMonthlyStats,
  getProfilePrioritiesWeighted,
  type RecentDecisionItem,
  type MonthlyStatsResponse,
  type WeightedPriority,
} from '../services/api';

// ---------------------------------------------------------------------------
// 1. RecentDecisionsRow
// ---------------------------------------------------------------------------

interface RecentDecisionsRowProps {
  onSeeAll?: () => void;
  onItemPress?: (comparisonId: string) => void;
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
  return (
    <TouchableOpacity
      testID="profile-recent-card"
      style={styles.miniCard}
      onPress={onPress}
      activeOpacity={0.7}
    >
      <View style={styles.miniRow}>
        <View style={[styles.miniTile, styles.miniTileMuted]}>
          <Text style={styles.miniTileGlyph}>•</Text>
        </View>
        <View style={styles.miniVsPill}>
          <Text style={styles.miniVsText}>{t('profile.recent.vs')}</Text>
        </View>
        <View style={[styles.miniTile, styles.miniTileWinner]}>
          <Text style={styles.miniTileGlyph}>•</Text>
        </View>
      </View>
      <Text style={styles.miniMeta} numberOfLines={1}>
        {item.winner_name} · {timeAgo(item.created_at, t)}
      </Text>
    </TouchableOpacity>
  );
}

export function RecentDecisionsRow({ onSeeAll, onItemPress }: RecentDecisionsRowProps) {
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
        setItems([]);
        setLoaded(true);
      });
    return () => {
      mounted = false;
    };
  }, []);

  if (!loaded || !items || items.length === 0) return null;

  return (
    <View testID="profile-recent-decisions" style={styles.section}>
      <View style={styles.sectionHeader}>
        <Text style={styles.sectionEyebrow}>
          {t('profile.recent.title')}
        </Text>
        {onSeeAll && (
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
        {items.map((it) => (
          <MiniVsCard
            key={it.comparison_id}
            item={it}
            t={t}
            onPress={onItemPress ? () => onItemPress(it.comparison_id) : undefined}
          />
        ))}
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

  if (!loaded || !priorities || priorities.length === 0) return null;

  return (
    <View testID="profile-priorities-inline" style={styles.prioritiesCard}>
      <Text style={styles.prioritiesTitle}>
        {t('profile.priorities.title')}
      </Text>
      <View style={styles.prioritiesList}>
        {priorities.map((p) => (
          <View key={p.key} style={styles.prioritiesRow}>
            <Text style={styles.prioritiesLabel} numberOfLines={1}>
              {t(p.label_key, p.key)}
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

  // Hide on threshold miss (Backend pattern — matches /home/savings hide gate).
  if (!loaded || !stats || !stats.threshold_met) return null;

  const showBonus = stats.bonus_credits_this_month > 0;

  return (
    <View testID="profile-month-strip" style={styles.monthStrip}>
      <View style={styles.statTile}>
        <Text style={styles.statNumber}>{stats.decisions_count}</Text>
        <Text style={styles.statLabel}>{t('profile.month.decisions')}</Text>
      </View>
      <View style={styles.statTile}>
        <Text style={[styles.statNumber, styles.statNumberAccent]}>
          {stats.savings_bhd.toFixed(0)}
        </Text>
        <Text style={styles.statLabel}>{t('profile.month.savings')}</Text>
      </View>
      {showBonus && (
        <View style={styles.statTile}>
          <Text style={styles.statNumber}>
            +{stats.bonus_credits_this_month}
          </Text>
          <Text style={styles.statLabel}>{t('profile.month.bonus')}</Text>
        </View>
      )}
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
  },
  miniTileMuted: {
    backgroundColor: '#E8E9ED',
  },
  miniTileWinner: {
    backgroundColor: '#1B1C1F',
    borderWidth: 2,
    borderColor: colors.accent,
  },
  miniTileGlyph: {
    color: 'rgba(0,0,0,0.18)',
    fontSize: 14,
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
