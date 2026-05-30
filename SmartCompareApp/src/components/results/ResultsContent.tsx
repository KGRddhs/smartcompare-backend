/**
 * Bundle E S3 — Lane A2 — ResultsContent
 *
 * Source of truth: docs/claude-design-handoff/ui_kits/mobile/ResultsScreen.jsx
 * (lines 1-410, especially the top-down composition at 286-407)
 *
 * This is the PURE PRESENTATION layer extracted from the 1956-line
 * ResultsScreen.tsx. ResultsScreen is now a thin orchestrator that owns:
 *  - SSE / loading / error / empty-state branches
 *  - scoring_v2 + personalization derivation
 *  - DemographicsBottomSheet, ShareBottomSheet, Loop 1 toast
 *  - trackEvents pendingEventsRef batching on unmount
 *
 * Everything visual lives here, in JSX top-down element order:
 *  1. Header (back + TopMatchBadge + share)
 *  2. Product pair hero (with vs pill on divider) + image_url slots
 *  3. "Why this fits you" verdict block
 *  4. Confidence pills (with "What we know" eyebrow)
 *  5. Cohort badge (single-line softened paragraph)
 *  6. DimensionBars (winners/losers per dim)
 *  7. PersonalizationChip (hides when applied_shifts empty)
 *  8. ConfidenceDetailsSheet (modal-style, driven by sheetLeg)
 *  9. ResultsAccordion ("Dig deeper" — Reviews + Pros & Cons + Specs)
 * 10. FeedbackCard ("Was this helpful?")
 *
 * image_url slot — A4 wires <Image source={{uri: product.image_url}} /> in
 * a follow-up PR. For now, A2 provides the placeholder slot at the
 * JSX-cited position with neutral fallback.
 */

import React from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
} from 'react-native';
import Animated, {
  FadeIn,
  FadeInDown,
  useAnimatedStyle,
  type SharedValue,
} from 'react-native-reanimated';
import { ArrowLeft, Share2, Smartphone } from 'lucide-react-native';
import { useTranslation } from 'react-i18next';

import { colors, spacing, radii, typography } from '../../theme';
import type { Product, ComparisonResult } from '../../types';
import { CohortBadge } from '../CohortBadge';
import FeedbackCard from '../FeedbackCard';
import { TopMatchBadge } from './TopMatchBadge';
import { HeroRings } from './HeroRings';
import { DimensionBars } from './DimensionBars';
import { FactualVerdict } from './FactualVerdict';
import { ConfidencePills } from './ConfidencePills';
import { ConfidenceDetailsSheet } from './ConfidenceDetailsSheet';
import { PersonalizationChip } from './PersonalizationChip';
import { RevealBurst } from '../hero/RevealBurst';
import { ResultsAccordion } from './ResultsAccordion';
import { anyEstimated } from '../../services/sourceMethod';

type SheetLeg = 'price' | 'reviews' | 'specs' | null;

export interface ResultsContentProps {
  result: ComparisonResult;
  products: Product[];
  winnerIndex: 0 | 1;
  scoring_v2: any | undefined;
  comparisonId: string | undefined;
  cohortPeerCount: number;
  cohortGovernorate: string;
  isRTL: boolean;

  feedbackSubmitted: boolean;
  onFeedbackSubmitted: () => void;
  feedbackComparisonId: string | undefined;

  sheetLeg: SheetLeg;
  onPillPress: (leg: 'price' | 'reviews' | 'specs') => void;
  onCloseSheet: () => void;

  winnerRevealed: boolean;
  winnerScaleAnimStyle: ReturnType<typeof useAnimatedStyle>;

  onBack: () => void;
  onShare: () => void;
}

export function ResultsContent({
  result,
  products,
  winnerIndex,
  scoring_v2,
  comparisonId,
  cohortPeerCount,
  cohortGovernorate,
  isRTL,
  feedbackSubmitted,
  onFeedbackSubmitted,
  feedbackComparisonId,
  sheetLeg,
  onPillPress,
  onCloseSheet,
  winnerRevealed,
  winnerScaleAnimStyle,
  onBack,
  onShare,
}: ResultsContentProps) {
  const { t } = useTranslation();

  const formatPrice = (price?: Product['price']) => {
    if (!price || price.unavailable || price.amount === null)
      return t('results.priceNA');
    return `${price.currency} ${price.amount.toLocaleString()}`;
  };

  // Per JSX, verdict body uses recommendation. For new format, overview.winner.reason.
  const isNewFormat = !!(result as any)?.overview?.winner;
  const verdictBody = isNewFormat
    ? (result as any)?.overview?.winner?.reason
    : (result as any)?.recommendation;
  const verdictCaption = isNewFormat
    ? (result as any)?.overview?.winner?.key_tradeoff
    : null;

  // For ResultsAccordion data
  const reviewProducts = isNewFormat
    ? (result as any)?.reviews?.products
    : undefined;
  const specsProducts = isNewFormat
    ? (result as any)?.specs?.products
    : undefined;

  return (
    <View style={styles.container} testID="results-content">
      {/* ─── # 1 Header — back + TopMatchBadge + share (JSX 297-311) ─── */}
      <View style={styles.header} testID="results-content-header">
        <TouchableOpacity
          testID="results-content-back-btn"
          accessibilityRole="button"
          accessibilityLabel="Back"
          style={styles.headerCircleBtn}
          onPress={onBack}
        >
          <ArrowLeft size={18} color={colors.text.primary} />
        </TouchableOpacity>

        <View style={styles.headerCenter}>
          <TopMatchBadge testID="results-content-top-match" />
        </View>

        <TouchableOpacity
          testID="results-content-share-btn"
          accessibilityRole="button"
          accessibilityLabel="Share"
          style={styles.headerCircleBtn}
          onPress={onShare}
        >
          <Share2 size={18} color={colors.text.primary} />
        </TouchableOpacity>
      </View>

      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.scrollContent}
      >
        {/* ─── # 2 Hero — product pair with "vs" pill divider (JSX 316-333) ─── */}
        <Animated.View
          entering={FadeIn.duration(400)}
          style={styles.heroPair}
          testID="results-content-hero-pair"
        >
          {products.map((product, idx) => {
            const isWinner = idx === winnerIndex;
            const wrapperStyle = isWinner
              ? [styles.productCardWrapper, winnerScaleAnimStyle]
              : styles.productCardWrapper;
            return (
              <Animated.View
                key={idx}
                style={wrapperStyle}
                testID={isWinner ? 'winner-card-anim' : undefined}
              >
                <View
                  style={[
                    styles.productCard,
                    isWinner ? styles.productCardWinner : styles.productCardBase,
                  ]}
                  testID={`results-product-card-${idx}`}
                >
                  {/* image_url slot — A4 wires <Image> in follow-up PR.
                      For now: neutral placeholder square per JSX 50-58. */}
                  <View
                    style={styles.productImageSlot}
                    testID={`results-product-image-slot-${idx}`}
                  >
                    <Smartphone
                      size={32}
                      color={colors.text.placeholder}
                      strokeWidth={1.5}
                    />
                  </View>
                  <Text style={styles.productName} numberOfLines={2}>
                    {product.name}
                  </Text>
                  {product.brand ? (
                    <Text style={styles.productSub} numberOfLines={1}>
                      {product.brand}
                    </Text>
                  ) : null}
                  <Text
                    style={[
                      styles.productPrice,
                      product.price?.unavailable
                        ? styles.productPriceUnavailable
                        : null,
                    ]}
                  >
                    {formatPrice(product.price)}
                  </Text>
                </View>
              </Animated.View>
            );
          })}

          {/* vs pill on the divider — absolute centered (JSX 319-331) */}
          <View
            style={styles.vsPillAbs}
            pointerEvents="none"
            testID="results-content-vs-pill"
          >
            <View style={styles.vsPill}>
              <Text style={styles.vsPillText}>VS</Text>
            </View>
          </View>
        </Animated.View>

        {/* ─── # 3 "Why this fits you" verdict block (JSX 336-346) ─── */}
        <Animated.View
          entering={FadeInDown.delay(200).duration(400)}
          style={styles.section}
          testID="results-content-why"
        >
          <Text style={styles.eyebrow}>{t('results.whyWePicked')}</Text>
          {scoring_v2 && scoring_v2.factual_verdict?.line1 && (
            <FactualVerdict
              line1={scoring_v2.factual_verdict.line1 ?? ''}
              line2={scoring_v2.factual_verdict.line2 ?? ''}
              testID="results-content-factual-verdict"
            />
          )}
          {!(scoring_v2 && scoring_v2.factual_verdict?.line1) && (
            <>
              <Text style={styles.verdictBody}>{verdictBody}</Text>
              {verdictCaption ? (
                <>
                  <Text style={styles.verdictRunnerUpEyebrow}>
                    {t('results.runnerUpWins')}
                  </Text>
                  <Text style={styles.verdictCaption}>{verdictCaption}</Text>
                </>
              ) : null}
            </>
          )}
        </Animated.View>

        {/* ─── # 4 Confidence pills + "What we know" eyebrow (JSX 356-365) ─── */}
        {scoring_v2?.confidence_legs ? (
          <Animated.View
            entering={FadeInDown.delay(300).duration(400)}
            style={styles.section}
            testID="results-content-confidence"
          >
            <Text style={styles.eyebrow}>{t('results.whatWeKnow')}</Text>
            <ConfidencePills
              confidence={scoring_v2.confidence_legs}
              hidePricePill={anyEstimated(products)}
              onPillPress={onPillPress}
              testID="results-content-confidence-pills"
            />
          </Animated.View>
        ) : null}

        {/* ─── # 5 Cohort badge — single-line softened paragraph (JSX 367-377) ─── */}
        <View
          style={styles.cohortSlot}
          testID="results-cohort-badge-slot"
        >
          <CohortBadge
            peerCount={cohortPeerCount}
            governorate={cohortGovernorate}
            isRTL={isRTL}
          />
        </View>

        {/* ─── # 6 scoring_v2 hero card ───
            Bundle E § Decision 2/3 — scoring_v2 hero card. Bundle C § 2e —
            in weird-mode the hero rings + TopMatchBadge are suppressed and
            replaced by a calm em-dash placeholder. Verdict text (rewritten
            by backend prompt in weird-mode) carries the meaning. NO banner
            anywhere — per FIVE critical rules #1. */}
        {scoring_v2 && scoring_v2.dimensions && scoring_v2.dimensions.length >= 3
          ? (() => {
              const isWeird = scoring_v2.comparison_quality === 'weird';
              return (
                <Animated.View
                  entering={FadeInDown.delay(400).duration(400)}
                  style={styles.section}
                  testID="results-scoring-v2"
                >
                  {!isWeird && winnerRevealed ? (
                    <View style={styles.topMatchSlot}>
                      <View
                        style={styles.revealBurstSlot}
                        pointerEvents="none"
                        testID="results-v2-reveal-burst-slot"
                      >
                        <RevealBurst
                          key={comparisonId || 'no-comparison-id'}
                          fireOnce
                          particleCount={6}
                          size={220}
                        />
                      </View>
                    </View>
                  ) : null}

                  {isWeird ? (
                    <View style={styles.weirdHero}>
                      <Text
                        style={styles.weirdHeroEmDash}
                        testID="results-v2-hero-em-dash"
                      >
                        {'\u2014'}
                      </Text>
                    </View>
                  ) : (
                    <HeroRings
                      scoreA={scoring_v2.overall_score?.product_a ?? 0}
                      scoreB={scoring_v2.overall_score?.product_b ?? 0}
                      winnerIndex={winnerIndex}
                      testID="results-v2-hero-rings"
                    />
                  )}

                  <PersonalizationChip
                    appliedShifts={scoring_v2.personalization?.applied_shifts}
                    testID="results-v2-personalization-chip"
                  />

                  <DimensionBars
                    dimensions={scoring_v2.dimensions}
                    winnerIndex={winnerIndex}
                    testID="results-v2-bars"
                  />

                  {sheetLeg ? (
                    <ConfidenceDetailsSheet
                      visible
                      leg={sheetLeg}
                      details={scoring_v2.confidence_details ?? {}}
                      onClose={onCloseSheet}
                      testID="results-v2-confidence-sheet"
                    />
                  ) : null}
                </Animated.View>
              );
            })()
          : null}

        {/*
         * Bundle E § Decision 3 one-release backward-compat. When the
         * payload carries legacy `scoring` but NOT `scoring_v2`, render a
         * minimal placeholder so older cached comparisons don't show an
         * empty hero. The new scoring_v2 path is the canonical surface
         * Bundle E S3 onwards; this is a defensive fallback only.
         *
         * The literal `!scoring_v2 && scoring` expression below is the
         * regression-pin for Task 3.5 backward-compat (see
         * __tests__/screens/ResultsScreen.integration.test.tsx).
         */}
        {(() => {
          const scoring = (result as any)?.scoring;
          return !scoring_v2 && scoring ? (
            <View
              testID="results-legacy-scoring-fallback"
              style={styles.section}
            />
          ) : null;
        })()}

        {/* ─── # 7 "Dig deeper" accordion (JSX 105-211 / consumed 381) ─── */}
        <Animated.View
          entering={FadeInDown.delay(500).duration(400)}
          style={styles.section}
          testID="results-content-accordion"
        >
          <ResultsAccordion
            products={products}
            reviewProducts={reviewProducts}
            specsProducts={specsProducts}
            testID="results-content-accordion-inner"
          />
        </Animated.View>

        {/* ─── # 8 Feedback prompt (JSX 384-404) ─── */}
        <Animated.View
          entering={FadeInDown.delay(600).duration(400)}
          style={styles.section}
          testID="results-content-feedback"
        >
          <FeedbackCard
            comparisonId={feedbackComparisonId}
            submitted={feedbackSubmitted}
            onSubmitted={onFeedbackSubmitted}
          />
        </Animated.View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bg.primary,
  },

  // Header — borderless, centered TopMatchBadge between two circular icon buttons
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingTop: 50,
    paddingHorizontal: spacing.base,
    paddingBottom: spacing.sm,
  },
  headerCircleBtn: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: colors.bg.secondary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  headerCenter: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },

  scroll: { flex: 1 },
  scrollContent: {
    paddingHorizontal: spacing.base,
    paddingTop: spacing.sm,
    paddingBottom: spacing['3xl'],
  },

  // Product pair hero
  heroPair: {
    flexDirection: 'row',
    gap: 10,
    marginBottom: 20,
    position: 'relative',
  },
  productCardWrapper: {
    flex: 1,
    minWidth: 0,
  },
  productCard: {
    borderRadius: 20,
    padding: 14,
    gap: 10,
  },
  productCardBase: {
    backgroundColor: colors.bg.secondary,
    borderWidth: 1,
    borderColor: colors.border.light,
  },
  productCardWinner: {
    backgroundColor: colors.accentLight,
    borderWidth: 2,
    borderColor: colors.accent,
  },
  productImageSlot: {
    aspectRatio: 1,
    borderRadius: 14,
    backgroundColor: '#EEEFF4',
    alignItems: 'center',
    justifyContent: 'center',
  },
  productName: {
    fontSize: 15,
    fontWeight: '600',
    color: colors.text.primary,
    lineHeight: 15 * 1.3,
  },
  productSub: {
    fontSize: 12,
    color: colors.text.secondary,
    lineHeight: 12 * 1.4,
  },
  productPrice: {
    fontSize: 18,
    fontWeight: '700',
    color: colors.text.primary,
    marginTop: 'auto',
  },
  productPriceUnavailable: {
    color: colors.text.secondary,
    fontSize: 14,
  },

  vsPillAbs: {
    position: 'absolute',
    top: 0,
    bottom: 0,
    left: 0,
    right: 0,
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1,
  },
  vsPill: {
    height: 24,
    paddingHorizontal: 10,
    borderRadius: 999,
    backgroundColor: colors.accentLight,
    borderWidth: 2,
    borderColor: colors.bg.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  vsPillText: {
    fontSize: 11,
    fontWeight: '700',
    color: colors.accentDark,
    letterSpacing: 1.1,
  },

  // Sections — consistent verdict / confidence / scoring_v2 wrappers
  section: {
    marginBottom: spacing.base,
    backgroundColor: colors.bg.secondary,
    borderRadius: radii.card,
    padding: spacing.base,
    borderWidth: 1,
    borderColor: colors.border.light,
  },
  eyebrow: {
    fontSize: 11,
    fontWeight: '600',
    color: colors.text.secondary,
    letterSpacing: 1.1,
    textTransform: 'uppercase',
    marginBottom: 8,
  },
  verdictBody: {
    fontSize: 18,
    fontWeight: '600',
    color: colors.text.primary,
    lineHeight: 18 * 1.45,
  },
  verdictCaption: {
    fontSize: 13,
    color: colors.text.secondary,
    marginTop: 8,
    lineHeight: 13 * 1.5,
  },
  verdictRunnerUpEyebrow: {
    fontSize: 11,
    fontWeight: '600',
    color: colors.text.secondary,
    letterSpacing: 1.1,
    textTransform: 'uppercase',
    marginTop: 12,
    marginBottom: 4,
  },

  cohortSlot: {
    marginBottom: spacing.base,
  },

  // scoring_v2 hero specifics
  topMatchSlot: {
    position: 'relative',
    alignItems: 'center',
    justifyContent: 'center',
  },
  revealBurstSlot: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    alignItems: 'center',
    justifyContent: 'center',
  },
  weirdHero: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: spacing.xl,
  },
  weirdHeroEmDash: {
    ...typography.display,
    color: colors.text.secondary,
    textAlign: 'center',
  },
});

export default ResultsContent;
