/**
 * Bundle E S3 — Lane A2 — ResultsContent (REWRITE 2026-06-02)
 *
 * Source of truth: docs/claude-design-handoff/ui_kits/mobile/ResultsScreen.jsx
 * (top-down composition at lines 286-407 of the JSX reference).
 *
 * This is the PURE PRESENTATION layer extracted from the 1956-line
 * ResultsScreen.tsx orchestrator. The orchestrator owns:
 *  - SSE / loading / error / empty-state branches
 *  - scoring_v2 + personalization derivation
 *  - DemographicsBottomSheet, ShareBottomSheet, Loop 1 toast
 *  - trackEvents pendingEventsRef batching on unmount
 *
 * JSX top-down element order (anchors pinned by
 * `__tests__/components/ResultsContent.rewriteOrder.test.tsx`):
 *  1. Header           — back / TopMatchBadge / share        (JSX 297-311)
 *  2. Hero pair        — two ProductCards + "vs" pill        (JSX 316-333)
 *  3. Why this fits you — eyebrow + verdict + runner-up cap
 *                        + PersonalizationChip subline        (JSX 336-346)
 *  4. Dimension bars   — DimensionBars + RevealBurst + sheet (JSX 348-353)
 *                        (Faithful-results Phase 2.1 pruned the HeroRings
 *                         score-rings card + its weird-mode em-dash stand-in)
 *  5. Confidence pills — "What we know" eyebrow              (JSX 356-365)
 *  6. Cohort badge     — softened single-line paragraph      (JSX 367-377)
 *  7. Dig deeper       — Reviews / Pros & Cons / Specs       (JSX 105-211, 381)
 *  8. Feedback prompt  — Accurate / Detailed / Fast chips    (JSX 384-404)
 *
 * Prior structure interleaved verdict → confidence → cohort → scoring_v2
 * hero → accordion which inverted the JSX ordering of scoring vs cohort
 * vs confidence. This REWRITE realigns the block sequence to the JSX
 * top-down while preserving every Bundle C/D/E scoring_v2 / personalization
 * / weird-mode / RevealBurst contract (verified by the existing test
 * suite — those testIDs and conditionals are reproduced verbatim, only
 * relocated within the scroll body).
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
import { ArrowLeft, Share2 } from 'lucide-react-native';
import { useTranslation } from 'react-i18next';

import { colors, spacing, radii } from '../../theme';
import type { Product, ComparisonResult } from '../../types';
import { CohortBadge } from '../CohortBadge';
import FeedbackCard from '../FeedbackCard';
import { TopMatchBadge } from './TopMatchBadge';
import { DimensionBars } from './DimensionBars';
import { FactualVerdict } from './FactualVerdict';
import { RunnerUpWinsCard } from './RunnerUpWinsCard';
import { ConfidencePills } from './ConfidencePills';
import { ConfidenceDetailsSheet } from './ConfidenceDetailsSheet';
import { PersonalizationChip } from './PersonalizationChip';
import { RevealBurst } from '../hero/RevealBurst';
// W1 walk-fix 2026-06-18 — CategoryProfile now lives INSIDE the "Dig deeper"
// accordion (ResultsAccordion), not as a standalone block here.
import { ResultsAccordion } from './ResultsAccordion';
import { SCORE_INTERNALS_RE } from './_deltaText';
import { anyEstimated } from '../../services/sourceMethod';
import { ProductImage } from '../primitives/ProductImage';

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
    // Phase 4.3 — price-pending: when the backend marks a price
    // `unavailable` (reason pending_genuine | size_mismatch) we render an
    // engaging "coming soon" line rather than a number or a bare "N/A".
    // No "estimated", no scary copy.
    if (price?.unavailable) return t('results.price.pending');
    if (!price || price.amount === null) return t('results.priceNA');
    return `${price.currency} ${price.amount.toLocaleString()}`;
  };

  // Phase 4.3 — when ANY product's price is pending we suppress the price
  // comparison surfaces (the Price dimension bar row + the Price confidence
  // pill) so we never show a price delta that doesn't exist, and we strip
  // the price clause from the headline below.
  const pricePending = products.some((p) => p.price?.unavailable === true);

  // WS-F Task F2 (FE-8) — fragrance compares routinely hit the 30s
  // STREAM_HARD_CAP and return `metadata.partial === true` (a best-available
  // assembly, NOT an error). Surface the existing calm `results.partial.note`
  // one-liner so a partial compare reads as "still settling," never broken.
  const isPartial = (result as any)?.metadata?.partial === true;

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
  // Lane A-L3 Task L3.2 — forward the per-row winner array (when L1
  // emits it) so the spec table can paint emerald per row. Tasks L3.3
  // wires the same accordion to the overall winnerIndex for the
  // pros/cons star prefix.
  //
  // L2 cross-QA verdict (2026-06-08) caught a cross-lane shape mismatch:
  // L1's response_builder emits
  //   `specs_comparison: { rows: [...], product_0_advantages: [...], ... }`
  // (dict-with-rows, preserving the legacy advantages keys alongside the
  // new per-row array). Fixtures used during L3 development carried a
  // flat array shape. Accept both so prod renders emerald winner cells
  // even before backend converges on a single shape. Resilient to
  // future schema migrations either direction.
  const specsComparisonRaw = isNewFormat
    ? (result as any)?.specs?.specs_comparison
    : undefined;
  const specsComparison: Array<any> | undefined = Array.isArray(specsComparisonRaw)
    ? specsComparisonRaw
    : Array.isArray(specsComparisonRaw?.rows)
      ? specsComparisonRaw.rows
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
                  {/* Bundle E S3 A4 Wave 2 — ProductImage primitive consumes
                      product.image_url (A3 contract `8c299ce`). 4-state
                      fallback: string→<Image>, null/undefined/onError→
                      placeholder. JSX:50-58 (aspectRatio 1, radius 14,
                      neutral #EEEFF4 placeholder tone). */}
                  <ProductImage
                    testID={`results-product-image-slot-${idx}`}
                    imageUrl={product.image_url}
                    aspectRatio={1}
                    borderRadius={14}
                    resizeMode="contain"
                    style={styles.productImageSlot}
                  />
                  <Text style={styles.productName} numberOfLines={2}>
                    {product.name}
                  </Text>
                  {product.brand ? (
                    <Text style={styles.productSub} numberOfLines={1}>
                      {product.brand}
                    </Text>
                  ) : null}
                  {/* Lane A-L3 Task L3.1 — variant string (e.g. "128GB · Black")
                      surfaces below the brand sub on each card. Backend writes
                      `overview.products[i].variant` per design Screen 1.
                      Hidden when missing or empty so legacy data + low-confidence
                      categories don't render an empty line. */}
                  {product.variant ? (
                    <Text
                      testID={`results-product-variant-${idx}`}
                      style={styles.productVariant}
                      numberOfLines={1}
                    >
                      {product.variant}
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
          style={styles.sectionLean}
          testID="results-content-why"
        >
          <Text style={styles.eyebrow}>{t('results.whyWePicked')}</Text>
          {/* WS-F Task F2 (FE-8) — partial-result affordance. When the compare
              hit the hard-cap (`metadata.partial === true`) show the existing
              calm one-liner here, just under the verdict eyebrow, so it reads
              as "still settling" rather than broken. Copy-policy clean. */}
          {isPartial ? (
            <Text
              testID="results-content-partial-note"
              style={styles.partialNote}
            >
              {t('results.partial.note')}
            </Text>
          ) : null}
          {/* Faithful-results Phase 2.2 (FE BUG #4): the runner-up caption was
              previously gated INTO the else-branch of `factual_verdict.line1`,
              so whenever the backend emitted a factual verdict (≈ always) the
              "where the runner-up wins" line — generated by the verdict prompt
              as `overview.winner.key_tradeoff` — was silently dropped. We now
              render the winner verdict (FactualVerdict when present, else the
              recommendation body) AND, independently, the runner-up caption
              whenever `key_tradeoff` exists. Two orthogonal blocks, no XOR. */}
          {scoring_v2 && scoring_v2.factual_verdict?.line1 ? (
            <FactualVerdict
              line1={scoring_v2.factual_verdict.line1 ?? ''}
              line2={scoring_v2.factual_verdict.line2 ?? ''}
              testID="results-content-factual-verdict"
            />
          ) : typeof verdictBody === 'string' &&
            SCORE_INTERNALS_RE.test(verdictBody) ? (
            // A6 defense-in-depth: drop a verdict body that leaks raw score
            // internals ("N-point", "/100", "overall score", "score of N")
            // rather than show the leak. Backend (WS-A) is canonical; this
            // fails a future regression loud-but-clean.
            null
          ) : (
            <Text style={styles.verdictBody}>{verdictBody}</Text>
          )}
          {/* Task #24 2026-06-18 — the inline one-line runner-up caption that
              used to render here moved into the richer structured
              <RunnerUpWinsCard> block below (after this verdict section). */}
          {/* Phase 4.4 — PersonalizationChip relocated here, directly under
              the "Why this fits you" headline (mockup subline "Weighted ↑
              Camera ↑ Battery — based on your priorities", JSX 343-345). It
              previously lived inside the scoring_v2 hero card. */}
          {scoring_v2 ? (
            <PersonalizationChip
              appliedShifts={scoring_v2.personalization?.applied_shifts}
              testID="results-v2-personalization-chip"
            />
          ) : null}
        </Animated.View>

        {/* ─── # 3b "Where the runner-up wins" card (Task #24) ───
            Richer structured runner-up block — replaces the old one-line
            caption that lived in the verdict block above. Lists the dims the
            runner-up actually leads (derived from scoring_v2.dimensions) +
            the verdict prompt's key_tradeoff prose. Self-hides when there's
            neither a winning dim nor key_tradeoff (no empty card). Gray, not
            emerald; placed between the verdict and the dimension bars. */}
        <RunnerUpWinsCard
          products={products}
          winnerIndex={winnerIndex}
          dimensions={scoring_v2?.dimensions}
          keyTradeoff={verdictCaption}
          testID="results-content-runner-up-wins"
        />

        {/* ─── # 4 Dimension bars (JSX 348-353) ───
            Faithful-results Phase 2.1 — the design's slot between the verdict
            and the confidence pills holds DimensionBars ONLY. The prior
            scoring_v2 "hero card" stacked a HeroRings score-rings panel (and a
            weird-mode em-dash placeholder standing in for those rings) on top
            of the bars — neither is in the Qaren design-system Results layout
            (ResultsScreen.jsx), which shows three dimension bars directly. Both
            are pruned. The winner-reveal celebration (RevealBurst, the emerald
            "winner reveal" signal-color moment) is preserved — it is a
            non-visual particle overlay, not the rings card — and stays gated
            to normal-mode + winnerRevealed. ConfidenceDetailsSheet (opened by a
            confidence-pill tap) also stays.

            NO banner anywhere — per the five critical rules #1; weird-mode
            meaning is carried by the backend-rewritten verdict prose above. */}
        {scoring_v2 && scoring_v2.dimensions && scoring_v2.dimensions.length >= 3
          ? (() => {
              const isWeird = scoring_v2.comparison_quality === 'weird';
              return (
                <Animated.View
                  entering={FadeInDown.delay(300).duration(400)}
                  style={styles.sectionLean}
                  testID="results-scoring-v2"
                >
                  {!isWeird && winnerRevealed ? (
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
                  ) : null}

                  {/* Walk-fix 2026-06-17 — when prices pend, drop BOTH `price`
                      and the price-derived `value` dim (no real data). (Belt-
                      and-suspenders: DimensionBars also drops any
                      caption_key:'limited_data' dim.) */}
                  <DimensionBars
                    dimensions={
                      pricePending
                        ? scoring_v2.dimensions.filter(
                            (d: any) => d?.key !== 'price' && d?.key !== 'value',
                          )
                        : scoring_v2.dimensions
                    }
                    winnerIndex={winnerIndex}
                    productAName={products[0]?.name}
                    productBName={products[1]?.name}
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

        {/* ─── # 5 Confidence pills + "What we know" eyebrow (JSX 356-365) ─── */}
        {scoring_v2?.confidence_legs ? (
          <Animated.View
            entering={FadeInDown.delay(400).duration(400)}
            style={styles.sectionLean}
            testID="results-content-confidence"
          >
            <Text style={styles.eyebrow}>{t('results.whatWeKnow')}</Text>
            <ConfidencePills
              confidence={scoring_v2.confidence_legs}
              hidePricePill={anyEstimated(products) || pricePending}
              onPillPress={onPillPress}
              testID="results-content-confidence-pills"
            />
          </Animated.View>
        ) : null}

        {/* ─── # 6 Cohort badge — single-line softened paragraph (JSX 367-377) ─── */}
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

        {/* W1 walk-fix 2026-06-18 — CategoryProfile moved OUT of this standalone
            slot and INTO the "Dig deeper" accordion (first section). A standalone
            "At a glance" block here confused users into thinking they had to pick
            a category before comparing; folding it into the accordion (one tap
            away, alongside Specs) reads as the curated highlight it is. See
            ResultsAccordion.tsx. */}

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
        {/* Accordion renders its OWN bordered panel card (matching the design's
            "Dig deeper" card) + its own bottom margin — so the wrapper is lean
            (no extra card) to avoid the prior double-card. */}
        <Animated.View
          entering={FadeInDown.delay(500).duration(400)}
          style={styles.sectionLean}
          testID="results-content-accordion"
        >
          <ResultsAccordion
            products={products}
            reviewProducts={reviewProducts}
            specsProducts={specsProducts}
            specsComparison={specsComparison}
            winnerIndex={winnerIndex}
            testID="results-content-accordion-inner"
          />
        </Animated.View>

        {/* ─── # 8 Feedback prompt (JSX 384-404) ─── */}
        {/* FeedbackCard renders its OWN card + margins, so the wrapper carries
            no chrome (avoids the prior double-card). */}
        <Animated.View
          entering={FadeInDown.delay(600).duration(400)}
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
  // Lane A-L3 Task L3.1 — variant tag below brand on the product card.
  productVariant: {
    fontSize: 11,
    color: colors.text.secondary,
    lineHeight: 11 * 1.4,
    marginTop: 2,
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

  // Faithful-results Phase 2.3 — LEAN section chrome. The Qaren design-system
  // Results layout (`ResultsScreen.jsx`) renders the verdict, dimension bars,
  // and confidence pills directly on the page background — eyebrow + content,
  // separated only by vertical rhythm (the design's `marginBottom: 24`). The
  // prior `styles.section` wrapped every block in a bordered secondary-bg card,
  // which (a) diverged from the design and (b) double-carded the accordion and
  // feedback prompt (both render their OWN card). Lean = spacing only.
  sectionLean: {
    marginBottom: spacing.xl,
  },

  // Carded wrapper — retained ONLY for the legacy-scoring backward-compat
  // placeholder (an intentionally-empty card shown for old cached comparisons
  // that carry `scoring` but not `scoring_v2`). Real content sections are lean.
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
  // WS-F Task F2 (FE-8) — calm partial-result one-liner under the verdict
  // eyebrow. Secondary tone so it reads as a soft "still settling" note, not
  // an alarm.
  partialNote: {
    fontSize: 13,
    color: colors.text.secondary,
    lineHeight: 13 * 1.4,
    marginBottom: 8,
  },
  // Task #24 — the inline runner-up caption styles (verdictCaption /
  // verdictRunnerUpEyebrow) moved into RunnerUpWinsCard.tsx.

  cohortSlot: {
    marginBottom: spacing.base,
  },

  // Winner-reveal celebration overlay. Absolute-fills the dimension-bars
  // section card (its nearest positioned ancestor) so the emerald RevealBurst
  // particles fire over the bars. Faithful-results Phase 2.1 removed the
  // former relative `topMatchSlot` wrapper (it anchored the pruned HeroRings);
  // the section View is itself the positioning context now.
  revealBurstSlot: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    alignItems: 'center',
    justifyContent: 'center',
  },
});

export default ResultsContent;
