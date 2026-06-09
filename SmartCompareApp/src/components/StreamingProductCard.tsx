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
import { View, Text, StyleSheet, I18nManager, Pressable } from 'react-native';
import { addScreenshotListener } from 'expo-screen-capture';
import { CounterTicker } from './CounterTicker';
import { colors, spacing, typography, radii } from '../theme';

/**
 * Pain-workflow signals the card can emit (B.1 F3.5). The parent threads
 * these to trackEvent -> POST /events; the backend pain_workflow derivation
 * (B.2) maps them onto pain_workflow_events later.
 *   - 'spec_expand'    : user revealed specs past the 3-row preview (too_many_specs)
 *   - 'result_abandon' : card unmounted before the 'verdict' stage (abandonment)
 *   - 'screenshot'     : OS screenshot taken while the card was on screen
 */
export type PainSignal = 'spec_expand' | 'result_abandon' | 'screenshot';

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
  /**
   * Pain-workflow signal sink (B.1 F3.5). When omitted, the card is a pure
   * render — no expand affordance, no abandon/screenshot effects — so the
   * existing loading-card call sites and tests are unaffected. When provided,
   * the parent wires it to trackEvent.
   */
  onSignal?: (signal: PainSignal) => void;
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

export function StreamingProductCard({ stage, product, testID, onSignal }: Props) {
  const tid = (suffix: string) => (testID ? `${testID}-${suffix}` : undefined);

  const showTitle = !!product?.name;
  const showSpecs = reached(stage, 'specs') && !!product?.specs;
  const showPrice = reached(stage, 'prices') && product?.price?.amount != null;
  const showRating = reached(stage, 'reviews') && product?.rating != null;

  // --- Pain-workflow instrumentation (only active when onSignal is wired) ---
  const [specsExpanded, setSpecsExpanded] = React.useState(false);

  // result_abandon: fire on unmount iff the card never reached the verdict
  // stage. `stage` is read through a ref so the cleanup sees the LATEST stage,
  // not the value captured when the (mount-only) effect first ran.
  const stageRef = React.useRef(stage);
  stageRef.current = stage;
  React.useEffect(() => {
    if (!onSignal) return;
    return () => {
      if (STAGE_RANK[stageRef.current] < STAGE_RANK.verdict) {
        onSignal('result_abandon');
      }
    };
    // Mount/unmount only — re-subscribing per stage would mis-fire abandon.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [onSignal]);

  // screenshot: listen while mounted; clean up the subscription on unmount.
  React.useEffect(() => {
    if (!onSignal) return;
    const sub = addScreenshotListener(() => onSignal('screenshot'));
    return () => sub.remove();
  }, [onSignal]);

  const handleSpecExpand = () => {
    if (specsExpanded) return; // signal once — first reveal is the pain signal
    setSpecsExpanded(true);
    onSignal?.('spec_expand');
  };

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

      {/* Specs slot — show 1-3 spec rows once stage reaches 'specs'.
          When instrumented (onSignal wired) and there are more than 3 specs,
          a "+N more" affordance reveals the rest and fires spec_expand. */}
      {showSpecs ? (
        (() => {
          const entries = Object.entries(product!.specs!).filter(
            ([, v]) => v !== null && v !== undefined && v !== ''
          );
          const PREVIEW = 3;
          const hiddenCount = entries.length - PREVIEW;
          const canExpand = !!onSignal && hiddenCount > 0;
          const visible = specsExpanded ? entries : entries.slice(0, PREVIEW);
          return (
            <View testID={tid('specs')} style={styles.specsBlock}>
              {visible.map(([k, v]) => (
                <View key={k} style={styles.specRow}>
                  <Text style={styles.specKey}>{prettyKey(k)}</Text>
                  <Text style={styles.specValue} numberOfLines={1}>{String(v)}</Text>
                </View>
              ))}
              {canExpand && !specsExpanded ? (
                <Pressable
                  testID={tid('spec-expand')}
                  onPress={handleSpecExpand}
                  hitSlop={8}
                  style={styles.specExpand}
                >
                  <Text style={styles.specExpandText}>{`+${hiddenCount} more`}</Text>
                </Pressable>
              ) : null}
            </View>
          );
        })()
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
  specExpand: {
    paddingTop: spacing.xs,
    alignSelf: I18nManager.isRTL ? 'flex-end' : 'flex-start',
  },
  specExpandText: {
    ...typography.caption,
    color: colors.accent,
    fontWeight: '600',
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
