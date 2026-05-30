/**
 * Bundle D 2.F.2 Screen 1 — HomeScreen editorial sections (un-deferred).
 *
 * Four optional sections rendered below the CompareCard:
 *   1. SmartPickCard       — "Smart pick of the day" personalized winner story
 *      (Backend: GET /api/v1/home/smart-pick)
 *   2. QuickCategories     — 4-tile category grid (static, no backend)
 *   3. SavingsBanner       — dark "This month ~X BHD shopped smarter" banner
 *      (Backend: GET /api/v1/home/savings — hidden when threshold_met=false)
 *   4. TrendingNearYou     — region-aware trending product pairs
 *      (Backend: GET /api/v1/home/trending — auth-optional)
 *
 * Each backend-driven section silently hides on empty_state / threshold-miss /
 * network failure. Build Principle #4 — never frame the app as scary.
 *
 * Source-of-truth visual: docs/claude-design-handoff/ui_kits/mobile/HomeScreen.jsx
 * lines 438-651.
 */

import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
} from 'react-native';
import { useTranslation } from 'react-i18next';
import { Check, TrendingUp } from 'lucide-react-native';
import { colors, spacing, radii, typography } from '../theme';
import {
  getHomeSmartPick,
  getHomeSavings,
  getHomeTrending,
  type HomeSmartPickItem,
  type HomeSavingsResponse,
  type HomeTrendingItem,
} from '../services/api';
import { deriveTone } from '../utils/deriveTone';
import { ProductImage } from './primitives/ProductImage';

// ---------------------------------------------------------------------------
// 1. SmartPickCard
// ---------------------------------------------------------------------------

interface SmartPickCardProps {
  onPressVerdict?: (comparisonId: string) => void;
}

export function SmartPickCard({ onPressVerdict }: SmartPickCardProps) {
  const { t } = useTranslation();
  const [pick, setPick] = useState<HomeSmartPickItem | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let mounted = true;
    getHomeSmartPick()
      .then((r) => {
        if (!mounted) return;
        setPick(r.empty_state ? null : r.smart_pick);
        setLoaded(true);
      })
      .catch(() => {
        if (!mounted) return;
        setPick(null);
        setLoaded(true);
      });
    return () => {
      mounted = false;
    };
  }, []);

  if (!loaded || !pick) return null;

  // Null-hide-surround rule (Bundle E ruling): hide each surround (eyebrow
  // pill, updated_at chip, per-product sub-line, verdict_short caption)
  // when its source field is null. NO fabrication.
  const showCategory = Boolean(pick.category);
  const showUpdatedAt = Boolean(pick.updated_at);
  const showWinnerSub = Boolean(pick.winner_sub);
  const showRunnerUpSub = Boolean(pick.runner_up_sub);
  const showVerdictShort = Boolean(pick.verdict_short);

  // Tone-driven PickTile colors via deriveTone (JSX: each tile background
  // is a brand-derived hex). Winner gets the more saturated tone +
  // emerald 2px outline; runner-up gets the muted complement.
  const winnerTone = deriveTone(pick.winner_name);
  const runnerUpTone = deriveTone(pick.runner_up_name);

  return (
    <View testID="home-smart-pick" style={styles.section}>
      <Text style={styles.eyebrow}>{t('home.smart_pick.title')}</Text>
      <View style={styles.smartCard}>
        {/* Header row: category eyebrow pill (left) + "Updated today" chip (right) */}
        {(showCategory || showUpdatedAt) ? (
          <View style={styles.smartHeader}>
            {showCategory ? (
              <View style={styles.smartCatPill} testID="home-smart-pick-category">
                <Text style={styles.smartCatPillText}>
                  {(pick.category ?? '').toUpperCase()}
                </Text>
              </View>
            ) : <View />}
            {showUpdatedAt ? (
              <Text style={styles.smartUpdated} testID="home-smart-pick-updated">
                {pick.updated_at}
              </Text>
            ) : null}
          </View>
        ) : null}

        {/* PickTile pair with center vs pill */}
        <View style={styles.smartTilesRow}>
          <View
            style={[
              styles.smartTile,
              { backgroundColor: runnerUpTone },
            ]}
            testID="home-smart-pick-tile-runner-up"
          >
            {/* Bundle E S3 A4 Wave 2 — ProductImage at top of tile per
                HomeScreen.jsx:506-525 (aspectRatio 1, radius 12, tone
                placeholder). Consumes A3 dbf3a5f runner_up_image_url. */}
            <ProductImage
              testID="home-smart-pick-runner-up-image"
              imageUrl={pick.runner_up_image_url}
              placeholderTone={runnerUpTone}
              aspectRatio={1}
              borderRadius={12}
              style={styles.smartTileImage}
            />
            <Text style={styles.smartTileName} numberOfLines={1}>
              {pick.runner_up_name}
            </Text>
            {showRunnerUpSub ? (
              <Text style={styles.smartTileSub} numberOfLines={1}>
                {pick.runner_up_sub}
              </Text>
            ) : null}
            {pick.runner_up_price_bhd !== null ? (
              <Text style={styles.smartTilePrice}>
                {pick.runner_up_price_bhd.toFixed(0)} {t('home.smart_pick.bhd')}
              </Text>
            ) : null}
          </View>
          <View style={styles.smartVsPill} pointerEvents="none">
            <Text style={styles.smartVsText}>VS</Text>
          </View>
          <View
            style={[
              styles.smartTile,
              styles.smartTileWinner,
              { backgroundColor: winnerTone },
            ]}
            testID="home-smart-pick-tile-winner"
          >
            <View style={styles.smartTileCheck}>
              <Check size={10} color={colors.bg.primary} strokeWidth={4} />
            </View>
            {/* Bundle E S3 A4 Wave 2 — ProductImage at top of tile per
                HomeScreen.jsx:506-525. Consumes A3 dbf3a5f
                winner_image_url. */}
            <ProductImage
              testID="home-smart-pick-winner-image"
              imageUrl={pick.winner_image_url}
              placeholderTone={winnerTone}
              aspectRatio={1}
              borderRadius={12}
              style={styles.smartTileImage}
            />
            <Text
              style={[styles.smartTileName, styles.smartTileNameWinner]}
              numberOfLines={1}
            >
              {pick.winner_name}
            </Text>
            {showWinnerSub ? (
              <Text
                style={[styles.smartTileSub, styles.smartTileSubWinner]}
                numberOfLines={1}
              >
                {pick.winner_sub}
              </Text>
            ) : null}
            {pick.winner_price_bhd !== null ? (
              <Text style={[styles.smartTilePrice, styles.smartTilePriceWinner]}>
                {pick.winner_price_bhd.toFixed(0)} {t('home.smart_pick.bhd')}
              </Text>
            ) : null}
          </View>
        </View>

        {/* Verdict caption — prefer verdict_short when present, else fall
            back to the i18n-resolved reason_key (legacy path). */}
        {showVerdictShort ? (
          <Text style={styles.smartReason} testID="home-smart-pick-verdict-short">
            {pick.verdict_short}
          </Text>
        ) : (
          <Text style={styles.smartReason}>
            {t(pick.reason_key, pick.reason_params || {})}
          </Text>
        )}

        <TouchableOpacity
          testID="home-smart-pick-verdict"
          style={styles.smartCta}
          onPress={() => onPressVerdict?.(pick.comparison_id)}
        >
          <Text style={styles.smartCtaText}>
            {t('home.smart_pick.viewVerdict')}
          </Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

// ---------------------------------------------------------------------------
// 2. QuickCategories (static — no backend)
// ---------------------------------------------------------------------------

interface QuickCategoriesProps {
  onPickCategory?: (cat: string) => void;
}

const QUICK_CATS = [
  { v: 'electronics', glyph: '⌬', labelKey: 'home.cat.electronics' },
  { v: 'skincare', glyph: '✦', labelKey: 'home.cat.skincare' },
  { v: 'supplements', glyph: '◉', labelKey: 'home.cat.supplements' },
  { v: 'makeup', glyph: '◑', labelKey: 'home.cat.makeup' },
];

export function QuickCategories({ onPickCategory }: QuickCategoriesProps) {
  const { t } = useTranslation();
  return (
    <View testID="home-quick-categories" style={styles.section}>
      <Text style={styles.eyebrow}>{t('home.quickCats.title')}</Text>
      <View style={styles.catGrid}>
        {QUICK_CATS.map((c) => (
          <TouchableOpacity
            key={c.v}
            testID={`home-quick-cat-${c.v}`}
            style={styles.catTile}
            onPress={() => onPickCategory?.(c.v)}
            activeOpacity={0.7}
          >
            <View style={styles.catGlyph}>
              <Text style={styles.catGlyphText}>{c.glyph}</Text>
            </View>
            <Text style={styles.catLabel}>{t(c.labelKey)}</Text>
          </TouchableOpacity>
        ))}
      </View>
    </View>
  );
}

// ---------------------------------------------------------------------------
// 3. SavingsBanner
// ---------------------------------------------------------------------------

export function SavingsBanner() {
  const { t } = useTranslation();
  const [stats, setStats] = useState<HomeSavingsResponse | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let mounted = true;
    getHomeSavings()
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

  if (!loaded || !stats || !stats.threshold_met) return null;

  return (
    <View testID="home-savings-banner" style={styles.savingsBanner}>
      <View style={styles.savingsContent}>
        <Text style={styles.savingsEyebrow}>{t('home.savings.eyebrow')}</Text>
        <Text style={styles.savingsAmount}>
          ~{stats.savings_bhd.toFixed(0)} {t('home.savings.amount')}
        </Text>
        <Text style={styles.savingsCount}>
          {t('home.savings.count', { count: stats.decisions_count })}
        </Text>
      </View>
    </View>
  );
}

// ---------------------------------------------------------------------------
// 4. TrendingNearYou
// ---------------------------------------------------------------------------

interface TrendingNearYouProps {
  onPressTrending?: (query: string) => void;
}

export function TrendingNearYou({ onPressTrending }: TrendingNearYouProps) {
  const { t } = useTranslation();
  const [items, setItems] = useState<HomeTrendingItem[] | null>(null);
  const [region, setRegion] = useState<string>('bahrain');
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let mounted = true;
    getHomeTrending()
      .then((r) => {
        if (!mounted) return;
        setItems(r.trending || []);
        setRegion(r.region || 'bahrain');
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

  // JSX-wins (HomeScreen.jsx:608-650): each row uses category-tag pill
  // (left) + "{a} vs {b}" with INLINE emerald-colored "vs" text (center) +
  // tabular count + trending arrow (right). The "vs" here is the inline
  // text variant, NOT the center-positioned pill (dual-VS-pattern rule).
  //
  // F-S1.4-B1 fix: Ahmed's device walkthrough showed rows rendering
  // "vs 1247" with the product-name strings MISSING. Root cause: the
  // pre-split fields `a` and `b` arrive as undefined on legacy curated
  // rows or when the backend split-by-" vs " can't determine the parts.
  // Defensive splitting from `query` when either name is missing keeps
  // the row legible — never render bare " vs " without anchors.
  return (
    <View testID="home-trending" style={styles.section}>
      <Text style={styles.eyebrow}>
        {t('home.trending.title', { region: t(`home.region.${region}`, region) })}
      </Text>
      <View style={styles.trendingList}>
        {items.slice(0, 5).map((it, i) => {
          // Resolve product names: prefer pre-split a/b from the new
          // backend shape (dca8067). Fall back to query-split if either
          // pre-split field is missing OR empty. Final fallback: render
          // the raw query alone (no "vs" anchor) so we never ship a
          // bare " vs " row.
          let nameA = (it.a || '').trim();
          let nameB = (it.b || '').trim();
          if (!nameA || !nameB) {
            const raw = (it.query || '').trim();
            // Case-insensitive split on " vs " (the curated-query convention).
            const split = raw.split(/\s+vs\s+/i);
            if (split.length >= 2) {
              nameA = nameA || split[0].trim();
              nameB = nameB || split.slice(1).join(' vs ').trim();
            }
          }
          const hasBothNames = Boolean(nameA && nameB);
          const composedQuery =
            it.query || (hasBothNames ? `${nameA} vs ${nameB}` : (nameA || nameB || ''));
          const count = typeof it.count === 'number' ? it.count : it.view_count;
          return (
            <TouchableOpacity
              key={`${composedQuery}-${i}`}
              testID="home-trending-item"
              style={styles.trendingItem}
              onPress={() => onPressTrending?.(composedQuery)}
              activeOpacity={0.7}
            >
              {it.tag ? (
                <View style={styles.trendingTag}>
                  <Text style={styles.trendingTagText} numberOfLines={1}>
                    {it.tag.toUpperCase()}
                  </Text>
                </View>
              ) : null}
              <Text style={styles.trendingPair} numberOfLines={1}>
                {hasBothNames ? (
                  <>
                    {nameA}
                    <Text style={styles.trendingPairVs}> vs </Text>
                    {nameB}
                  </>
                ) : (
                  /* Defensive — if even the split fallback can't yield
                     two names, show whatever single string we have so
                     the row never collapses to bare " vs ". */
                  composedQuery
                )}
              </Text>
              <View style={styles.trendingCount}>
                <Text style={styles.trendingCountText}>{count}</Text>
                <TrendingUp size={11} color={colors.text.secondary} />
              </View>
            </TouchableOpacity>
          );
        })}
      </View>
    </View>
  );
}

// ---------------------------------------------------------------------------
// HomeEditorialSections — composed wrapper rendered below the CompareCard.
// S3 REWRITE: drops the internal ScrollView so the 4 sections render as
// flat siblings inside HomeScreen's main scroll per JSX:695-709. Hosts
// only a paddings View around the 4 child sections.
// ---------------------------------------------------------------------------

interface HomeEditorialSectionsProps {
  onPressVerdict?: (comparisonId: string) => void;
  onPickCategory?: (cat: string) => void;
  onPressTrending?: (query: string) => void;
}

export default function HomeEditorialSections(props: HomeEditorialSectionsProps) {
  return (
    <View
      testID="home-editorial"
      style={styles.scrollContent}
    >
      <SmartPickCard onPressVerdict={props.onPressVerdict} />
      <QuickCategories onPickCategory={props.onPickCategory} />
      <SavingsBanner />
      <TrendingNearYou onPressTrending={props.onPressTrending} />
    </View>
  );
}

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const styles = StyleSheet.create({
  scroll: {
    flex: 1,
  },
  scrollContent: {
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.md,
  },
  section: {
    marginTop: spacing.xl,
  },
  eyebrow: {
    ...typography.caption,
    fontWeight: '600',
    color: colors.text.secondary,
    textTransform: 'uppercase',
    letterSpacing: 1.1,
    marginBottom: spacing.sm,
  },
  // SmartPickCard
  smartCard: {
    padding: spacing.base,
    borderRadius: radii.card,
    backgroundColor: colors.bg.secondary,
    borderWidth: 1,
    borderColor: colors.border.light,
    gap: spacing.md,
  },
  smartHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  smartChip: {
    paddingHorizontal: spacing.sm,
    height: 22,
    borderRadius: 999,
    backgroundColor: colors.bg.primary,
    borderWidth: 1,
    borderColor: colors.border.light,
    alignItems: 'center',
    justifyContent: 'center',
  },
  smartChipText: {
    ...typography.small,
    fontWeight: '500',
    color: colors.text.secondary,
    letterSpacing: 0.6,
    textTransform: 'uppercase',
  },
  // Bundle E B4.3b additions per HomeScreen.jsx:438-501 (SmartPickCard
  // header row: category pill left + "Updated today" chip right).
  smartCatPill: {
    paddingHorizontal: spacing.sm,
    height: 22,
    borderRadius: 999,
    backgroundColor: colors.bg.primary,
    borderWidth: 1,
    borderColor: colors.border.light,
    alignItems: 'center',
    justifyContent: 'center',
  },
  smartCatPillText: {
    fontSize: 10,
    fontWeight: '500',
    lineHeight: 10 * 1.4,
    color: colors.text.secondary,
    letterSpacing: 0.6,
  },
  smartUpdated: {
    fontSize: 11,
    fontWeight: '500',
    lineHeight: 11,
    color: colors.accentDark,
  },
  smartTilesRow: {
    flexDirection: 'row',
    gap: spacing.sm,
    position: 'relative',
    alignItems: 'stretch',
  },
  smartTile: {
    flex: 1,
    padding: spacing.sm,
    borderRadius: 12,
    backgroundColor: colors.bg.primary,
    borderWidth: 1,
    borderColor: colors.border.light,
    gap: 4,
  },
  // Bundle E S3 A4 Wave 2 — ProductImage tile inside SmartPick PickTile.
  // Per HomeScreen.jsx:506-525 the image box itself carries the tone +
  // radius 12 + aspectRatio 1. ProductImage's own placeholderTone +
  // aspectRatio + borderRadius props handle the visual; this style only
  // adds tile-internal margin so it doesn't collide with the check chip.
  smartTileImage: {
    marginBottom: 4,
  },
  smartTileMuted: {
    opacity: 0.7,
  },
  smartTileWinner: {
    borderColor: colors.accent,
    borderWidth: 2,
  },
  smartTileCheck: {
    position: 'absolute',
    top: 6,
    right: 6,
    width: 18,
    height: 18,
    borderRadius: 9,
    backgroundColor: colors.accent,
    alignItems: 'center',
    justifyContent: 'center',
  },
  smartTileName: {
    ...typography.caption,
    fontWeight: '600',
    color: colors.text.primary,
  },
  smartTileNameWinner: {
    fontWeight: '700',
  },
  // Bundle E spec sub-line (per HomeScreen.jsx PickTile sub) — sits below
  // the product name, before the price. Hidden via null-hide-surround
  // when winner_sub / runner_up_sub is null from backend.
  smartTileSub: {
    fontSize: 11,
    fontWeight: '500',
    lineHeight: 11 * 1.4,
    color: colors.text.secondary,
  },
  smartTileSubWinner: {
    color: colors.text.primary,
  },
  smartTilePrice: {
    ...typography.small,
    color: colors.text.secondary,
  },
  smartTilePriceWinner: {
    color: colors.text.primary,
    fontWeight: '600',
  },
  smartVsPill: {
    position: 'absolute',
    left: '50%',
    top: '50%',
    transform: [{ translateX: -16 }, { translateY: -12 }],
    height: 24,
    paddingHorizontal: spacing.sm,
    borderRadius: 999,
    backgroundColor: colors.accentLight,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 2,
    borderColor: colors.bg.secondary,
    zIndex: 1,
  },
  smartVsText: {
    ...typography.small,
    fontWeight: '700',
    color: colors.accentDark,
    letterSpacing: 1.1,
    textTransform: 'uppercase',
  },
  smartReason: {
    ...typography.caption,
    fontWeight: '500',
    color: colors.text.primary,
  },
  smartCta: {
    width: '100%',
    height: 40,
    borderRadius: 999,
    backgroundColor: colors.bg.primary,
    borderWidth: 1,
    borderColor: colors.text.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  smartCtaText: {
    ...typography.caption,
    fontWeight: '600',
    color: colors.text.primary,
  },
  // QuickCategories
  catGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
  },
  catTile: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.md,
    minHeight: 56,
    borderRadius: 14,
    backgroundColor: colors.bg.secondary,
    borderWidth: 1,
    borderColor: colors.border.light,
    width: '48%',
  },
  catGlyph: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: colors.bg.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  catGlyphText: {
    fontSize: 14,
    fontWeight: '700',
    color: colors.accentDark,
  },
  catLabel: {
    ...typography.caption,
    fontWeight: '600',
    color: colors.text.primary,
  },
  // SavingsBanner
  savingsBanner: {
    marginTop: spacing.xl,
    padding: spacing.base,
    borderRadius: radii.card,
    backgroundColor: colors.bg.inverse,
    overflow: 'hidden',
  },
  savingsContent: {
    flex: 1,
  },
  savingsEyebrow: {
    ...typography.small,
    fontWeight: '500',
    color: 'rgba(255,255,255,0.55)',
    letterSpacing: 0.9,
    textTransform: 'uppercase',
  },
  savingsAmount: {
    ...typography.title,
    fontSize: 22,
    fontWeight: '700',
    color: colors.text.onInverse,
    marginTop: 2,
  },
  savingsCount: {
    ...typography.small,
    color: 'rgba(255,255,255,0.7)',
    marginTop: 2,
  },
  // TrendingNearYou
  trendingList: {
    gap: spacing.sm,
  },
  trendingItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.md,
    minHeight: 56,
    borderRadius: 14,
    backgroundColor: colors.bg.secondary,
    borderWidth: 1,
    borderColor: colors.border.light,
  },
  trendingQuery: {
    flex: 1,
    ...typography.caption,
    fontWeight: '500',
    color: colors.text.primary,
  },
  // Bundle E B4.3a additions per HomeScreen.jsx:608-650 — category tag
  // pill (left) + inline-vs pair (center) + count + trending arrow (right).
  trendingTag: {
    paddingHorizontal: 8,
    height: 20,
    borderRadius: 999,
    backgroundColor: colors.bg.primary,
    borderWidth: 1,
    borderColor: colors.border.light,
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  trendingTagText: {
    fontSize: 10,
    fontWeight: '500',
    lineHeight: 10,
    color: colors.text.secondary,
    letterSpacing: 0.6,
  },
  // Pre-split pair text — "iPhone 15 vs Galaxy S24" with the "vs" colored
  // emerald (inline, NOT a center-positioned pill — dual-VS-pattern rule).
  trendingPair: {
    flex: 1,
    minWidth: 0,
    fontSize: 13,
    fontWeight: '500',
    lineHeight: 13 * 1.3,
    color: colors.text.primary,
  },
  trendingPairVs: {
    color: colors.accentDark,
    fontWeight: '700',
  },
  trendingCount: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  trendingCountText: {
    ...typography.small,
    fontWeight: '500',
    color: colors.text.secondary,
  },
});
