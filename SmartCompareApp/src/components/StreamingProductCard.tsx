/**
 * StreamingProductCard — progressive-fill product card.
 *
 * Phase 3 Task 27. Used on the Results loading screen to render a
 * "ghost card" that progressively fills as SSE stages arrive. See
 * design § 3 — title fills first, then specs, then prices count up
 * via CounterTicker (Task 10), then star rating fades in.
 *
 * Stage gating (the parent passes the highest-completed SSE stage):
 *   init     → title skeleton only
 *   title    → title visible, specs skeleton, price/rating hidden
 *   specs    → title + specs visible, price/rating hidden
 *   prices   → title + specs + price visible, rating hidden
 *   reviews  → title + specs + price + rating visible
 *   verdict  → all slots final + steady (parent triggers reveal animation)
 *
 * The `product` prop is partial-shape on purpose — the orchestrator hands
 * us whatever the SSE stream has produced so far. Missing optional fields
 * never crash; they just stay in skeleton/hidden state.
 */

import React from 'react';
import { View, Text, StyleSheet, I18nManager } from 'react-native';
import { CounterTicker } from './CounterTicker';
import { colors, spacing, typography, radii } from '../theme';

export type StreamingStage =
  | 'init'
  | 'title'
  | 'specs'
  | 'prices'
  | 'reviews'
  | 'verdict';

export interface StreamingProductLike {
  name?: string;
  specs?: Record<string, string | number | null | undefined>;
  price?: {
    amount?: number;
    currency?: string;
    retailer?: string;
  };
  rating?: number;
  reviewCount?: number;
}

interface Props {
  /** Highest-completed SSE stage. Higher stages reveal more slots. */
  stage: StreamingStage;
  /** Whatever SSE has produced so far (partial-shape allowed). */
  product?: StreamingProductLike;
  /** Optional hook for tests + parent to address slots. */
  testID?: string;
}

const STAGE_RANK: Record<StreamingStage, number> = {
  init: 0,
  title: 1,
  specs: 2,
  prices: 3,
  reviews: 4,
  verdict: 5,
};

function reached(current: StreamingStage, target: StreamingStage): boolean {
  return STAGE_RANK[current] >= STAGE_RANK[target];
}

export function StreamingProductCard({ stage, product, testID }: Props) {
  const tid = (suffix: string) => (testID ? `${testID}-${suffix}` : undefined);

  const showTitle = !!product?.name;
  const showSpecs = reached(stage, 'specs') && !!product?.specs;
  const showPrice = reached(stage, 'prices') && product?.price?.amount != null;
  const showRating = reached(stage, 'reviews') && product?.rating != null;

  return (
    <View testID={testID} style={styles.card}>
      {/* Title slot */}
      {showTitle ? (
        <Text testID={tid('title')} style={styles.title} numberOfLines={2}>
          {product!.name}
        </Text>
      ) : (
        <View testID={tid('title-skeleton')} style={[styles.skeleton, styles.skeletonTitle]} />
      )}

      {/* Specs slot — show 1-3 spec rows once stage reaches 'specs'. */}
      {showSpecs ? (
        <View testID={tid('specs')} style={styles.specsBlock}>
          {Object.entries(product!.specs!)
            .filter(([, v]) => v !== null && v !== undefined && v !== '')
            .slice(0, 3)
            .map(([k, v]) => (
              <View key={k} style={styles.specRow}>
                <Text style={styles.specKey}>{prettyKey(k)}</Text>
                <Text style={styles.specValue} numberOfLines={1}>{String(v)}</Text>
              </View>
            ))}
        </View>
      ) : showTitle ? (
        <View style={styles.skeletonStack}>
          <View style={[styles.skeleton, styles.skeletonRow]} />
          <View style={[styles.skeleton, styles.skeletonRow]} />
        </View>
      ) : null}

      {/* Price slot — counter ticker for the BHD value. */}
      {showPrice ? (
        <View testID={tid('price')} style={styles.priceRow}>
          <CounterTicker
            target={Math.round(product!.price!.amount!)}
            duration={800}
            suffix={` ${product!.price!.currency ?? 'BHD'}`}
            style={styles.priceText}
          />
          {product!.price!.retailer ? (
            <Text style={styles.retailerText} numberOfLines={1}>
              {product!.price!.retailer}
            </Text>
          ) : null}
        </View>
      ) : null}

      {/* Rating slot — star + numeric value. */}
      {showRating ? (
        <View testID={tid('rating')} style={styles.ratingRow}>
          <Text style={styles.ratingStar}>{'\u2605'}</Text>
          <Text style={styles.ratingValue}>
            {Number(product!.rating!).toFixed(1)}
          </Text>
          {product!.reviewCount ? (
            <Text style={styles.ratingMeta}>
              {`(${product!.reviewCount})`}
            </Text>
          ) : null}
        </View>
      ) : null}
    </View>
  );
}

function prettyKey(key: string): string {
  return key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.bg.secondary,
    borderRadius: radii.card,
    padding: spacing.lg,
    minHeight: 200,
    gap: spacing.md,
  },
  title: {
    ...typography.title,
    color: colors.text.primary,
  },
  specsBlock: {
    gap: spacing.xs,
  },
  specRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: spacing.sm,
  },
  specKey: {
    ...typography.caption,
    color: colors.text.secondary,
  },
  specValue: {
    ...typography.caption,
    color: colors.text.primary,
    fontWeight: '600',
    flexShrink: 1,
    // Trailing-edge alignment in spec rows — flips to 'left' under RTL so
    // the value stays opposite the spec label in both locales.
    textAlign: I18nManager.isRTL ? 'left' : 'right',
  },
  priceRow: {
    flexDirection: 'row',
    alignItems: 'baseline',
    gap: spacing.sm,
  },
  priceText: {
    ...typography.title,
    color: colors.text.primary,
    fontWeight: '700',
  },
  retailerText: {
    ...typography.caption,
    color: colors.text.secondary,
  },
  ratingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
  },
  ratingStar: {
    ...typography.body,
    color: colors.accent,
  },
  ratingValue: {
    ...typography.body,
    color: colors.text.primary,
    fontWeight: '600',
  },
  ratingMeta: {
    ...typography.caption,
    color: colors.text.secondary,
  },
  skeleton: {
    backgroundColor: colors.border.light,
    borderRadius: spacing.xs,
  },
  skeletonTitle: {
    height: 22,
    width: '70%',
  },
  skeletonStack: {
    gap: spacing.xs,
  },
  skeletonRow: {
    height: 12,
    width: '90%',
  },
});
