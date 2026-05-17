/**
 * Qaren - Results Screen (Single Scroll)
 * Converts 3-tab layout to single continuous scroll.
 * Preserves ALL business logic: SSE handling, event tracking, share, feedback.
 */
import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Share,
  Linking,
  Switch,
} from 'react-native';
import Animated, {
  FadeIn,
  FadeInDown,
  useSharedValue,
  useAnimatedStyle,
  withSpring,
} from 'react-native-reanimated';
// Bundle B/C/D Task 3.3 — winner-card reveal spring uses the shared
// progress config so the settle feels consistent with onboarding bars.
import { motion } from '../theme/motion';
import * as Haptics from 'expo-haptics';
import {
  ArrowLeft,
  Share2,
  ChevronDown,
  ChevronUp,
  Star,
  ExternalLink,
  Shield,
  AlertCircle,
  Trophy,
  Camera as CameraIcon,
  Battery,
  Monitor,
  Zap,
  HardDrive,
  DollarSign,
  Info,
  Award,
  Gift,
} from 'lucide-react-native';
import { useTranslation } from 'react-i18next';
import { NativeStackScreenProps } from '@react-navigation/native-stack';

import { colors, spacing, radii, typography, shadows } from '../theme';
import {
  RootStackParamList,
  Product,
  Comparison,
  RatingSource,
  ComparisonResult,
  ScoringResult,
  ProductScores,
  ScoreBreakdown,
  PersonalizedInsight,
  OverviewProduct,
  ReviewSummary,
  ReviewHighlight,
} from '../types';
import { Card } from '../components/Card';
import { SkeletonLoader } from '../components/SkeletonLoader';
import { ProgressBar } from '../components/ProgressBar';
import { CohortBadge } from '../components/CohortBadge';
import { useLanguage } from '../hooks/useLanguage';
import FeedbackCard from '../components/FeedbackCard';
import DemographicsBottomSheet from '../components/DemographicsBottomSheet';
import ShareBottomSheet from '../components/ShareBottomSheet';
import type { CreateShareResult } from '../services/referralService';
import {
  trackEvents,
  shareComparison,
  putDemographics,
  parseApiError,
  DemographicsPayload,
} from '../services/api';
import { LoadingRings } from '../components/illustrations/LoadingRings';
import { HeroRings } from '../components/results/HeroRings';
import { DimensionBars } from '../components/results/DimensionBars';
import { TopMatchBadge } from '../components/results/TopMatchBadge';
import { FactualVerdict } from '../components/results/FactualVerdict';
import { getUsageStatus, UsageStatus } from '../services/usageService';
import {
  loadDemographicsState,
  recordDismissal,
  recordSubmission,
  shouldShowDemographicsPrompt,
} from '../services/demographicsTrigger';
import { getSavedUser } from '../services/authService';

type ResultsScreenProps = NativeStackScreenProps<RootStackParamList, 'Results'>;

export default function ResultsScreen({ route, navigation }: ResultsScreenProps) {
  const { t } = useTranslation();
  // Bundle E Task 0.1 — History → Results crash: deep-link / stale-cache
  // navigations can hand us undefined `route.params`. Destructure defensively
  // so the empty-state branch can render instead of throwing on line 1.
  //
  // Bucket A bugs 1 + 2: ResultsScreen now handles three nav-param shapes
  //   route.params.result            → render directly (existing path)
  //   route.params.comparison_id     → fetch full payload via getComparison(id)
  //   route.params.vision_products   → identify+compare from camera URIs
  // We hold `result` in state so async loads flow into the same render path.
  const [result, setResult] = useState<ComparisonResult | null | undefined>(
    route?.params?.result
  );
  const [loadingResult, setLoadingResult] = useState<boolean>(
    !route?.params?.result &&
      !!(route?.params?.comparison_id || route?.params?.vision_products)
  );
  const [loadError, setLoadError] = useState<
    'not_found' | 'need_more_photos' | 'vision_failed' | 'generic' | null
  >(null);
  // 1.2s brand-moment floor (Qaren UX redesign § 3) — even fast fetches
  // wait this long so the LoadingRings hero animation lands.
  const minDisplayUntilRef = useRef<number>(Date.now() + 1200);
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);
  // Phase 3 § 4b — specs collapsed by default. The post-reveal moment
  // should feel like an answer, not a data dump; the user expands when
  // they want detail.
  const [specsExpanded, setSpecsExpanded] = useState(false);
  const { isRTL } = useLanguage();
  const [showDiffsOnly, setShowDiffsOnly] = useState(false);

  // Winner reveal animation state
  const [winnerRevealed, setWinnerRevealed] = useState(false);
  // Bundle B/C/D Task 3.3 — winner card scales 0.96 → 1.0 on reveal.
  // Worklet-native via Reanimated; settles in ~300ms via progress spring.
  const winnerScale = useSharedValue(0.96);
  const winnerAnimStyle = useAnimatedStyle(() => ({
    transform: [{ scale: winnerScale.value }],
  }));
  const [usageStatus, setUsageStatus] = useState<UsageStatus | null>(null);

  // Demographics prompt state
  const [demographicsVisible, setDemographicsVisible] = useState(false);
  const [demographicsError, setDemographicsError] = useState<string | null>(null);

  // Referral share sheet state (F2.3 + F2.4)
  const [shareSheetVisible, setShareSheetVisible] = useState(false);
  const [loop1ToastVisible, setLoop1ToastVisible] = useState(false);
  const [lifetimeRemaining, setLifetimeRemaining] = useState<number | null>(null);

  useEffect(() => {
    getUsageStatus().then(setUsageStatus);
  }, []);

  // Bucket A bug 1 — History tap path. Fetch the full payload when only
  // a comparison_id was passed. Respects the 1.2s brand-moment floor so
  // the LoadingRings animation lands even on instant cache hits.
  useEffect(() => {
    const comparisonId = route?.params?.comparison_id;
    if (!comparisonId || result) return;

    let cancelled = false;
    (async () => {
      try {
        const { getComparison } = await import('../services/api');
        const data = await getComparison(comparisonId);
        const remaining = minDisplayUntilRef.current - Date.now();
        if (remaining > 0) {
          await new Promise((resolve) => setTimeout(resolve, remaining));
        }
        if (!cancelled) {
          setResult(data);
          setLoadingResult(false);
        }
      } catch (err: any) {
        if (cancelled) return;
        const status = err?.response?.status;
        if (status === 404) {
          setLoadError('not_found');
        } else if (status === 401) {
          // Axios 401 interceptor handles refresh/redirect — no-op here.
        } else {
          setLoadError('generic');
        }
        setLoadingResult(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [route?.params?.comparison_id, result]);

  // Detect new structured format vs old flat format
  const isNewFormat = !!result?.overview?.winner;

  // Bundle A §5.3 — defensive products access. v1 (legacy) rows used
  // `result.products`; v2 (structured) rows use `result.overview.products`.
  // History list filter now hides v1, but old client caches and SSE stragglers
  // can still hit this with neither shape — render the empty state instead of
  // crashing on `result.products[i].name`.
  const products = ((result as any)?.overview?.products
    ?? (result as any)?.products
    ?? []) as Product[];
  const comparison = result?.comparison;
  const winner_index = isNewFormat ? result.overview!.winner.product_index : result?.winner_index;
  const recommendation = isNewFormat ? result.overview!.winner.reason : result?.recommendation;
  const key_differences = result?.key_differences;
  const metadata = result?.metadata;
  const scoring = result?.scoring;
  // Bundle E § Decision 2 — new dimensions[] contract. Backend emits
  // `scoring_v2` alongside legacy `scoring` for one release cycle.
  const scoring_v2 = (result as any)?.scoring_v2;

  // Event tracking
  const mountTimeRef = useRef(Date.now());
  const pendingEventsRef = useRef<
    Array<{ event_type: string; event_data?: Record<string, any>; comparison_id?: string }>
  >([]);
  const comparisonId = metadata?.query;

  const trackEvent = (eventType: string, eventData?: Record<string, any>) => {
    pendingEventsRef.current.push({
      event_type: eventType,
      event_data: eventData,
      comparison_id: comparisonId,
    });
  };

  useEffect(() => {
    // Winner reveal with haptic feedback + Bundle B/C/D Task 3.3 spring.
    const timer = setTimeout(async () => {
      setWinnerRevealed(true);
      winnerScale.value = withSpring(1, motion.springConfig.progress);
      try {
        await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
      } catch {}
    }, 800);

    return () => {
      clearTimeout(timer);
      // Send view duration + any pending events on unmount
      const durationMs = Date.now() - mountTimeRef.current;
      pendingEventsRef.current.push({
        event_type: 'result_view_duration',
        event_data: { duration_ms: durationMs },
        comparison_id: comparisonId,
      });
      if (pendingEventsRef.current.length > 0) {
        trackEvents(pendingEventsRef.current);
      }
    };
  }, []);

  // --- Helpers ---

  const formatPrice = (price?: Product['price']) => {
    if (!price || price.unavailable || price.amount === null) return t('results.priceNA');
    return `${price.currency} ${price.amount.toLocaleString()}`;
  };

  const getScoreColor = (score: number): string => {
    if (score > 70) return colors.accent;
    if (score >= 40) return colors.warning;
    return colors.destructive;
  };

  // F2.4: Result-aware CTA variant. Strong/close mapping per design 3.1.
  // 'saved' variant deferred until ResultsScreen Save tap actually persists state.
  const ctaVariant: 'strong' | 'close' | 'default' = (() => {
    const margin = scoring?.win_margin;
    if (typeof margin !== 'number') return 'default';
    if (margin >= 15) return 'strong';
    if (margin < 8) return 'close';
    return 'default';
  })();

  const sharableComparisonId =
    (result as any)?.comparison_id || (metadata as any)?.comparison_id;

  const winnerName = isNewFormat
    ? result!.overview!.winner.name
    : products[winner_index ?? 0]?.name;

  const handleShare = () => {
    if (!sharableComparisonId) {
      // Fall back to legacy Share.share when there's no persisted comparison
      // to invite from (e.g. anonymous flows that didn't save).
      Share.share({
        message: `Comparing ${products[0]?.name} vs ${products[1]?.name}\n\nWinner: ${winnerName}\n\n${recommendation}`,
      }).catch(() => { /* swallow */ });
      trackEvent('share', { method: 'text_only', cta_variant: ctaVariant });
      return;
    }
    trackEvent('share_sheet_opened', { cta_variant: ctaVariant });
    setShareSheetVisible(true);
  };

  const handleShareCompleted = (response: CreateShareResult) => {
    setShareSheetVisible(false);
    // Bundle B/C/D § 4.2 — backend now returns lifetime_invites_remaining
    // (3 lifetime per device). Defensive `?? null` for older share-endpoint
    // responses during the rollout window.
    setLifetimeRemaining(response.lifetime_invites_remaining ?? null);
    setLoop1ToastVisible(true);
    trackEvent('share_completed', {
      cta_variant: ctaVariant,
      lifetime_invites_remaining: response.lifetime_invites_remaining,
    });
    // Auto-dismiss the Loop 1 toast after 4s
    setTimeout(() => setLoop1ToastVisible(false), 4000);
  };

  const openRatingSource = (source: RatingSource | null | undefined) => {
    if (source?.url) {
      trackEvent('source_click', { source_name: source.name, url: source.url });
      Linking.openURL(source.url);
    }
  };

  // Demographics bottom-sheet trigger after results render (2s delay).
  // Schedule + dismissal cooldown live in services/demographicsTrigger.
  useEffect(() => {
    let cancelled = false;
    const timer = setTimeout(async () => {
      try {
        const user = await getSavedUser();
        if (!user) return; // anonymous flows don't get the prompt
        const state = await loadDemographicsState();
        const shouldShow = shouldShowDemographicsPrompt({
          ...state,
          // currentSessionIndex is conservative — using dismissedCount + 1 means
          // the predicate's "show on session AFTER each dismissal" rule passes.
          currentSessionIndex: state.dismissedCount + 1,
        });
        if (shouldShow && !cancelled) {
          setDemographicsVisible(true);
        }
      } catch {
        // best-effort; never block the results screen on this
      }
    }, 2000);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, []);

  const handleDemographicsSubmit = async (payload: DemographicsPayload) => {
    setDemographicsError(null);
    try {
      await putDemographics(payload);
      await recordSubmission();
      setDemographicsVisible(false);
      trackEvent('demographics_submitted', {
        all_skipped:
          payload.age_group === 'Prefer not to say' &&
          payload.gender === 'Prefer not to say' &&
          payload.governorate === 'Prefer not to say',
      });
    } catch (err: any) {
      const { message } = parseApiError(err);
      setDemographicsError(message || t('demographics.error.network'));
    }
  };

  const handleDemographicsSkip = async () => {
    try {
      await recordDismissal();
    } finally {
      setDemographicsVisible(false);
      trackEvent('demographics_dismissed');
    }
  };

  const getProductScores = (index: number): ProductScores | null => {
    if (!scoring) return null;
    return scoring.scores[`product_${index}`] ?? null;
  };

  // Price comparison: calculate % less
  const getPriceDiff = (): { cheaperIndex: number; percent: number } | null => {
    const p0 = products[0]?.price?.amount;
    const p1 = products[1]?.price?.amount;
    if (p0 == null || p1 == null || p0 === 0 || p1 === 0) return null;
    if (p0 < p1) return { cheaperIndex: 0, percent: Math.round(((p1 - p0) / p1) * 100) };
    if (p1 < p0) return { cheaperIndex: 1, percent: Math.round(((p0 - p1) / p0) * 100) };
    return null;
  };

  const SCORE_LABELS: Record<keyof ScoreBreakdown, string> = {
    price_score: 'Price',
    spec_score: 'Specs',
    review_score: 'Reviews',
    value_score: 'Value',
    reliability_score: 'Reliability',
    popularity_score: 'Popularity',
  };

  const priceDiff = getPriceDiff();

  // Specs filtering
  const HIDDEN_FIELDS = ['brand', 'model', 'variant', 'category'];
  const NA_VALUES = ['n/a', 'na', 'null', 'none', 'unknown', ''];

  const filterSpecs = (specs: Record<string, any>) => {
    return Object.entries(specs).filter(([key, value]) => {
      if (HIDDEN_FIELDS.includes(key)) return false;
      if (key.endsWith('_source')) return false;
      if (value === null || value === undefined) return false;
      if (typeof value === 'string' && NA_VALUES.includes(value.toLowerCase().trim())) return false;
      return true;
    });
  };

  // Get all spec keys across both products for diff comparison
  const getAllSpecKeys = (): string[] => {
    const keys = new Set<string>();
    const specsProducts = isNewFormat ? result?.specs?.products : products;
    specsProducts?.forEach((p: any) => {
      if (p.specs) {
        filterSpecs(p.specs).forEach(([k]) => keys.add(k));
      }
    });
    return Array.from(keys);
  };

  const isSpecDifferent = (key: string): boolean => {
    const specsProducts = isNewFormat ? result?.specs?.products : products;
    if (!specsProducts || specsProducts.length < 2) return true;
    const v0 = specsProducts[0]?.specs?.[key];
    const v1 = specsProducts[1]?.specs?.[key];
    return String(v0) !== String(v1);
  };

  // Bucket A bugs 1 + 2: theatrical loading state while the async fetch
  // (history payload or vision identify) is in flight. Renders LoadingRings
  // hero animation with copy specific to the source (history vs camera).
  if (loadingResult) {
    return (
      <View style={styles.container} testID="results-loading-state">
        <View style={styles.header}>
          <TouchableOpacity onPress={() => navigation.goBack()} style={styles.headerButton}>
            <ArrowLeft size={24} color={colors.text.primary} />
          </TouchableOpacity>
          <View style={{ flex: 1 }} />
          <View style={styles.headerButton} />
        </View>
        <View style={styles.loadingRingsContainer}>
          <LoadingRings size={120} />
          <Text style={styles.loadingRingsText}>
            {t('results.loading.fromHistory')}
          </Text>
        </View>
      </View>
    );
  }

  // Bundle E Task 0.1 — top-level defensive guard. `route.params.result`
  // is undefined for deep-links or stale history rehydrations; without
  // this branch every `result?.X` derivation below is fine but the JSX
  // would still render an unusable comparison shell. Bail to the
  // empty-state instead, matching the design § 1a intent.
  if (!result || loadError) {
    return (
      <View style={styles.container} testID="results-empty-state">
        <View style={styles.header}>
          <TouchableOpacity onPress={() => navigation.goBack()} style={styles.headerButton}>
            <ArrowLeft size={24} color={colors.text.primary} />
          </TouchableOpacity>
          <View style={{ flex: 1 }} />
          <View style={styles.headerButton} />
        </View>
        <View style={styles.emptyStateContainer}>
          <AlertCircle size={48} color={colors.text.secondary} />
          <Text style={styles.emptyStateTitle}>
            {loadError === 'not_found'
              ? t('results.emptyState.notFound')
              : t('results.emptyState.title')}
          </Text>
          <TouchableOpacity
            onPress={() => navigation.goBack()}
            style={styles.emptyStateCta}
            accessibilityRole="button"
          >
            <Text style={styles.emptyStateCtaText}>
              {t('results.emptyState.cta')}
            </Text>
          </TouchableOpacity>
        </View>
      </View>
    );
  }

  // Bundle A §5.3 — render the empty state instead of crashing on
  // `products[0].name` when the comparison payload is missing both shapes.
  // This is belt-and-braces against the v1 history filter; v2 rows are
  // gated at save time by _validate_renderable.
  if (products.length < 2) {
    return (
      <View style={styles.container} testID="results-empty-state">
        <View style={styles.header}>
          <TouchableOpacity onPress={() => navigation.goBack()} style={styles.headerButton}>
            <ArrowLeft size={24} color={colors.text.primary} />
          </TouchableOpacity>
          <View style={{ flex: 1 }} />
          <View style={styles.headerButton} />
        </View>
        <View style={styles.emptyStateContainer}>
          <Text style={styles.emptyStateTitle}>
            {t('results.empty.title', { defaultValue: "This one's not loading." })}
          </Text>
          <Text style={styles.emptyStateBody}>
            {t('results.empty.body', { defaultValue: 'Run a fresh comparison from Home.' })}
          </Text>
          <TouchableOpacity
            onPress={() => navigation.goBack()}
            style={styles.emptyStateCta}
            accessibilityRole="button"
          >
            <Text style={styles.emptyStateCtaText}>
              {t('results.empty.cta', { defaultValue: 'Go home' })}
            </Text>
          </TouchableOpacity>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()} style={styles.headerButton}>
          <ArrowLeft size={24} color={colors.text.primary} />
        </TouchableOpacity>
        <Text style={styles.headerTitle} numberOfLines={1}>
          {products[0]?.name} vs {products[1]?.name}
        </Text>
        <TouchableOpacity onPress={handleShare} style={styles.headerButton}>
          <Share2 size={20} color={colors.text.primary} />
        </TouchableOpacity>
      </View>

      {/* Category switched banner */}
      {(result as any)?.category_switched && (
        <View style={styles.categorySwitchedBanner}>
          <Info size={14} color={colors.accent} />
          <Text style={styles.categorySwitchedText}>
            {t('results.categorySwitched', { category: (result as any)?.category_used })}
          </Text>
        </View>
      )}

      <ScrollView style={styles.scroll} contentContainerStyle={styles.scrollContent}>
        {/* 1. Product Cards (side by side) */}
        <Animated.View entering={FadeIn.duration(400)} style={styles.productsRow}>
          {products.map((product, index) => {
            const isWinner = index === winner_index;
            const scores = getProductScores(index);
            const overviewProduct = isNewFormat ? result.overview!.products[index] : null;
            // Bundle B/C/D Task 3.3 — only the winner card scales; the
            // runner-up stays still so the visual emphasis lands.
            const cardWrapperStyle = isWinner
              ? [styles.productCardWrapper, winnerAnimStyle]
              : styles.productCardWrapper;

            return (
              <Animated.View
                key={index}
                testID={isWinner ? 'winner-card-anim' : undefined}
                style={cardWrapperStyle}
              >
              <Card
                variant={isWinner && winnerRevealed ? 'winner' : 'default'}
                style={styles.productCard}
              >
                {/* Best Pick badge */}
                {isWinner && winnerRevealed && (
                  <View style={styles.bestPickBadge}>
                    <Trophy size={12} color="#FFF" />
                    <Text style={styles.bestPickText}>{t('results.bestPick')}</Text>
                  </View>
                )}

                {/* Score badge */}
                {scores && (
                  <View style={[styles.scoreBadge, { borderColor: getScoreColor(scores.overall) }]}>
                    <Text style={[styles.scoreBadgeValue, { color: getScoreColor(scores.overall) }]}>
                      {Math.round(scores.overall)}
                    </Text>
                    <Text style={styles.scoreBadgeLabel}>/100</Text>
                  </View>
                )}

                <Text style={styles.brandText}>{product.brand}</Text>
                <Text style={styles.productName}>{product.name}</Text>

                {/* Price */}
                <Text style={[styles.priceText, product.price?.unavailable && styles.priceUnavailable]}>
                  {formatPrice(product.price)}
                </Text>
                {product.price?.source_method === 'converted_usd' && (
                  <Text style={styles.priceNote}>{t('results.convertedUSD')}</Text>
                )}
                {(product.price?.estimated || product.price?.source_method === 'estimated') && (
                  <Text style={styles.priceNote}>{t('results.estimated')}</Text>
                )}
                {product.price?.retailer && !product.price?.unavailable && (
                  <Text style={styles.retailerText}>{product.price.retailer}</Text>
                )}

                {/* Value badge */}
                {overviewProduct?.value_badge && (
                  <View
                    style={[
                      styles.valueBadge,
                      {
                        backgroundColor:
                          overviewProduct.value_badge === 'great_value'
                            ? colors.accentLight
                            : overviewProduct.value_badge === 'overpriced'
                            ? '#FEF2F2'
                            : colors.bg.secondary,
                      },
                    ]}
                  >
                    <Text
                      style={[
                        styles.valueBadgeText,
                        {
                          color:
                            overviewProduct.value_badge === 'great_value'
                              ? colors.accent
                              : overviewProduct.value_badge === 'overpriced'
                              ? colors.destructive
                              : colors.text.secondary,
                        },
                      ]}
                    >
                      {overviewProduct.value_badge === 'great_value'
                        ? t('results.value.greatValue')
                        : overviewProduct.value_badge === 'fair_price'
                        ? t('results.value.fairPrice')
                        : overviewProduct.value_badge === 'premium_price'
                        ? t('results.value.premium')
                        : t('results.value.overpriced')}
                    </Text>
                  </View>
                )}

                {/* Rating */}
                {product.rating != null ? (
                  <TouchableOpacity
                    style={styles.ratingRow}
                    onPress={() => openRatingSource(product.rating_source)}
                    disabled={!product.rating_source?.url}
                  >
                    <Star size={14} color={colors.warning} fill={colors.warning} />
                    <Text style={styles.ratingText}>{product.rating.toFixed(1)}</Text>
                    {product.review_count != null && (
                      <Text style={styles.reviewCountText}>
                        ({product.review_count.toLocaleString()})
                      </Text>
                    )}
                    {product.rating_source?.url && (
                      <ExternalLink size={10} color={colors.accent} />
                    )}
                  </TouchableOpacity>
                ) : (
                  <Text style={styles.noRatingText}>{t('results.noRating')}</Text>
                )}

                {/* Best for */}
                {overviewProduct?.best_for ? (
                  <Text style={styles.bestForText}>{t('results.bestForLabel', { useCase: overviewProduct.best_for })}</Text>
                ) : null}
              </Card>
              </Animated.View>
            );
          })}
        </Animated.View>

        {/* Confidence indicator */}
        {isNewFormat && result.overview!.confidence?.overall && (
          <View style={styles.confidenceBanner}>
            {result.overview!.confidence.overall === 'high' ? (
              <Shield size={14} color={colors.accent} />
            ) : (
              <AlertCircle size={14} color={colors.warning} />
            )}
            <Text
              style={[
                styles.confidenceText,
                {
                  color:
                    result.overview!.confidence.overall === 'high'
                      ? colors.accent
                      : result.overview!.confidence.overall === 'medium'
                      ? colors.warning
                      : colors.destructive,
                },
              ]}
            >
              {t(`results.confidence.${result.overview!.confidence.overall}`)}
            </Text>
          </View>
        )}

        {/* 2. Why we picked this — was "Verdict". Per design § 4g audit. */}
        <Animated.View entering={FadeInDown.delay(200).duration(400)} style={styles.section}>
          <Text style={styles.sectionTitle}>{t('results.whyWePicked')}</Text>
          <Text style={styles.verdictText}>{recommendation}</Text>
          {isNewFormat && result.overview!.winner.key_tradeoff ? (
            <Text style={styles.tradeoffNote}>{result.overview!.winner.key_tradeoff}</Text>
          ) : null}
        </Animated.View>

        {/* 2.5 Cohort badge — surfaces the cohort moat inline per § 4b /
            build principle 6. CohortBadge guards on peerCount<=0 +
            missing governorate so anonymous / low-confidence matches
            render nothing and the slot stays invisible. */}
        <View testID="results-cohort-badge-slot" style={styles.cohortBadgeSlot}>
          <CohortBadge
            peerCount={resolveCohortPeerCount(result)}
            governorate={resolveCohortGovernorate(result)}
            isRTL={isRTL}
          />
        </View>

        {/* F2.4: Result-aware share CTA — strong/close/default per design 3.1 */}
        {sharableComparisonId ? (
          <Animated.View entering={FadeInDown.delay(250).duration(400)} style={styles.section}>
            <TouchableOpacity
              style={styles.referralCta}
              onPress={handleShare}
              activeOpacity={0.8}
              accessibilityRole="button"
              accessibilityLabel={t(`referrals.cta.${ctaVariant}`)}
            >
              <Share2 size={18} color={colors.bg.primary} />
              <Text style={styles.referralCtaText}>
                {t(`referrals.cta.${ctaVariant}`)}
              </Text>
            </TouchableOpacity>
          </Animated.View>
        ) : null}

        {/* 3. Price comparison */}
        <Animated.View entering={FadeInDown.delay(300).duration(400)} style={styles.section}>
          <Text style={styles.sectionTitle}>{t('results.price')}</Text>
          {products.map((product, index) => (
            <View key={index} style={styles.priceCompRow}>
              <Text style={styles.priceCompName}>{product.name}</Text>
              <View style={styles.priceCompRight}>
                <Text style={styles.priceCompAmount}>{formatPrice(product.price)}</Text>
                {priceDiff && priceDiff.cheaperIndex === index && (
                  <View style={styles.priceLessBadge}>
                    <Text style={styles.priceLessText}>
                      {t('results.priceLess', { percent: priceDiff.percent })}
                    </Text>
                  </View>
                )}
              </View>
            </View>
          ))}
          {products[0]?.price?.retailer && (
            <Text style={styles.retailerAttribution}>{products[0].price.retailer}</Text>
          )}
        </Animated.View>

        {/* 4. Key Differences */}
        {isNewFormat && result.overview!.tradeoffs?.length > 0 ? (
          <Animated.View entering={FadeInDown.delay(400).duration(400)} style={styles.section}>
            <Text style={styles.sectionTitle}>{t('results.runnerUpWins')}</Text>
            {result.overview!.tradeoffs.map((tradeoff, i) => (
              <View key={i} style={styles.tradeoffRow}>
                <View style={styles.tradeoffItem}>
                  <Text style={styles.tradeoffProduct}>{tradeoff.winner_wins.product}</Text>
                  <Text style={styles.tradeoffDim}>
                    {tradeoff.winner_wins.dimension.replace(/_/g, ' ')} (+
                    {Math.round(tradeoff.winner_wins.margin)})
                  </Text>
                </View>
                <Text style={styles.tradeoffVs}>vs</Text>
                <View style={styles.tradeoffItem}>
                  <Text style={styles.tradeoffProduct}>{tradeoff.loser_wins.product}</Text>
                  <Text style={styles.tradeoffDim}>
                    {tradeoff.loser_wins.dimension.replace(/_/g, ' ')} (+
                    {Math.round(tradeoff.loser_wins.margin)})
                  </Text>
                </View>
              </View>
            ))}
          </Animated.View>
        ) : !isNewFormat && (key_differences?.length ?? 0) > 0 ? (
          <Animated.View entering={FadeInDown.delay(400).duration(400)} style={styles.section}>
            <Text style={styles.sectionTitle}>{t('results.runnerUpWins')}</Text>
            {key_differences!.map((diff, index) => (
              <Text key={index} style={styles.differenceItem}>
                {diff}
              </Text>
            ))}
          </Animated.View>
        ) : null}

        {/* 5. Personalized Insights */}
        {result.personalized_insights && result.personalized_insights.length > 0 && (
          <Animated.View entering={FadeInDown.delay(500).duration(400)} style={styles.section}>
            {result.personalized_insights.map((insight, index) => (
              <View key={index} style={styles.insightCard}>
                <Text style={styles.insightFocusArea}>
                  {insight.focus_area.replace(/_/g, ' ')}
                </Text>
                <Text style={styles.insightText}>{insight.insight}</Text>
              </View>
            ))}
          </Animated.View>
        )}

        {/* 6. Specs accordion (collapsed by default per § 4b). */}
        <Animated.View entering={FadeInDown.delay(600).duration(400)} style={styles.section}>
          <TouchableOpacity
            testID="results-specs-toggle"
            accessibilityRole="button"
            accessibilityState={{ expanded: specsExpanded }}
            style={styles.sectionHeader}
            onPress={() => setSpecsExpanded(!specsExpanded)}
          >
            <Text style={styles.sectionTitle}>{t('results.specs')}</Text>
            {specsExpanded ? (
              <ChevronUp size={20} color={colors.text.secondary} />
            ) : (
              <ChevronDown size={20} color={colors.text.secondary} />
            )}
          </TouchableOpacity>

          {specsExpanded && (
            <>
              {/* Show differences only toggle */}
              <View style={styles.diffToggleRow}>
                <Text style={styles.diffToggleLabel}>{t('results.specsShowDiff')}</Text>
                <Switch
                  value={showDiffsOnly}
                  onValueChange={setShowDiffsOnly}
                  trackColor={{ false: colors.border.medium, true: colors.accentLight }}
                  thumbColor={showDiffsOnly ? colors.accent : '#f4f3f4'}
                />
              </View>

              {/* Specs table */}
              <View style={styles.specsTable}>
                {/* Header row */}
                <View style={styles.specsTableRow}>
                  <Text style={[styles.specsTableCell, styles.specsKeyCell]}></Text>
                  {products.map((p, i) => (
                    <Text key={i} style={[styles.specsTableCell, styles.specsValueCell]} numberOfLines={1}>
                      {p.name}
                    </Text>
                  ))}
                </View>

                {/* Spec rows */}
                {getAllSpecKeys()
                  .filter((key) => !showDiffsOnly || isSpecDifferent(key))
                  .map((key) => {
                    const specsProducts = isNewFormat ? result.specs?.products : products;
                    const values = specsProducts?.map((p: any) => p.specs?.[key]);
                    const isDiff = isSpecDifferent(key);
                    // Determine winner for this spec (simple heuristic: higher number or existence)
                    let winnerIdx: number | null = null;
                    if (isDiff && values && values.length === 2) {
                      const n0 = parseFloat(String(values[0]));
                      const n1 = parseFloat(String(values[1]));
                      if (!isNaN(n0) && !isNaN(n1) && n0 !== n1) {
                        winnerIdx = n0 > n1 ? 0 : 1;
                      }
                    }

                    return (
                      <View key={key} style={styles.specsTableRow}>
                        <Text style={[styles.specsTableCell, styles.specsKeyCell]}>
                          {key.replace(/_/g, ' ')}
                        </Text>
                        {values?.map((val: any, i: number) => (
                          <View key={i} style={[styles.specsTableCell, styles.specsValueCell]}>
                            <Text style={styles.specsValueText}>
                              {val != null ? String(val) : '-'}
                            </Text>
                            {winnerIdx === i && (
                              <View style={styles.winnerDot} />
                            )}
                          </View>
                        ))}
                      </View>
                    );
                  })}
              </View>
            </>
          )}
        </Animated.View>

        {/* 7. Reviews */}
        {isNewFormat && result.reviews?.products ? (
          <Animated.View entering={FadeInDown.delay(700).duration(400)} style={styles.section}>
            <Text style={styles.sectionTitle}>{t('results.reviews')}</Text>
            {result.reviews.products.map((rp: any, index: number) => {
              const summary: ReviewSummary | undefined = rp.review_summary;
              if (!rp.rating && !summary?.consensus && (!summary?.highlights || summary.highlights.length === 0)) {
                return null;
              }
              return (
                <Card key={index} style={styles.reviewCard}>
                  <Text style={styles.reviewCardTitle}>{rp.name}</Text>

                  {rp.rating != null && (
                    <TouchableOpacity
                      style={styles.ratingRow}
                      onPress={() => rp.rating_source?.url && openRatingSource(rp.rating_source)}
                      disabled={!rp.rating_source?.url}
                    >
                      <Star size={14} color={colors.warning} fill={colors.warning} />
                      <Text style={styles.ratingText}>{rp.rating.toFixed(1)}</Text>
                      {rp.review_count != null && (
                        <Text style={styles.reviewCountText}>
                          ({rp.review_count.toLocaleString()})
                        </Text>
                      )}
                      {rp.rating_source?.name && (
                        <Text style={styles.sourceText}>{rp.rating_source.name}</Text>
                      )}
                    </TouchableOpacity>
                  )}

                  {summary?.consensus ? (
                    <Text style={styles.consensusText}>{summary.consensus}</Text>
                  ) : null}

                  {summary?.highlights && summary.highlights.length > 0 && (
                    <View style={styles.highlightsSection}>
                      {summary.highlights.map((h: ReviewHighlight, i: number) => (
                        <Text
                          key={i}
                          style={[
                            styles.highlightItem,
                            {
                              color:
                                h.sentiment === 'positive' ? colors.accent : colors.destructive,
                            },
                          ]}
                        >
                          {h.sentiment === 'positive' ? '+' : '-'} {h.point}
                        </Text>
                      ))}
                    </View>
                  )}

                  {summary?.agreement_level === 'divided' && (
                    <Text style={styles.dividedNote}>
                      {t('results.reviews.divided')}
                    </Text>
                  )}
                </Card>
              );
            })}
          </Animated.View>
        ) : (
          /* Old format reviews: pros/cons */
          products.some(
            (p) =>
              (p.pros && p.pros.length > 0) ||
              (p.cons && p.cons.length > 0) ||
              p.rating
          ) && (
            <Animated.View entering={FadeInDown.delay(700).duration(400)} style={styles.section}>
              <Text style={styles.sectionTitle}>{t('results.reviews')}</Text>
              {products.map((product, index) => (
                <Card key={index} style={styles.reviewCard}>
                  <Text style={styles.reviewCardTitle}>{product.name}</Text>

                  {product.rating != null && (
                    <TouchableOpacity
                      style={styles.ratingRow}
                      onPress={() => openRatingSource(product.rating_source)}
                      disabled={!product.rating_source?.url}
                    >
                      <Star size={14} color={colors.warning} fill={colors.warning} />
                      <Text style={styles.ratingText}>{product.rating.toFixed(1)}</Text>
                      {product.review_count != null && (
                        <Text style={styles.reviewCountText}>
                          ({product.review_count.toLocaleString()})
                        </Text>
                      )}
                    </TouchableOpacity>
                  )}

                  {product.pros && product.pros.length > 0 && (
                    <View style={styles.highlightsSection}>
                      {product.pros.map((pro, i) => (
                        <Text key={i} style={[styles.highlightItem, { color: colors.accent }]}>
                          + {pro}
                        </Text>
                      ))}
                    </View>
                  )}

                  {product.cons && product.cons.length > 0 && (
                    <View style={styles.highlightsSection}>
                      {product.cons.map((con, i) => (
                        <Text
                          key={i}
                          style={[styles.highlightItem, { color: colors.destructive }]}
                        >
                          - {con}
                        </Text>
                      ))}
                    </View>
                  )}
                </Card>
              ))}
            </Animated.View>
          )
        )}

        {/* 8a. Bundle E § Decision 2/3 — scoring_v2 hero card */}
        {scoring_v2 && scoring_v2.dimensions && scoring_v2.dimensions.length >= 3 && (
          <Animated.View entering={FadeInDown.delay(750).duration(400)} style={styles.section} testID="results-scoring-v2">
            <TopMatchBadge testID="results-v2-top-match" />
            <HeroRings
              scoreA={scoring_v2.overall_score?.product_a ?? 0}
              scoreB={scoring_v2.overall_score?.product_b ?? 0}
              winnerIndex={
                (scoring_v2.overall_score?.product_a ?? 0) >=
                (scoring_v2.overall_score?.product_b ?? 0)
                  ? 0
                  : 1
              }
              testID="results-v2-hero-rings"
            />
            {scoring_v2.factual_verdict?.line1 && (
              <FactualVerdict
                line1={scoring_v2.factual_verdict.line1 ?? ''}
                line2={scoring_v2.factual_verdict.line2 ?? ''}
                testID="results-v2-factual-verdict"
              />
            )}
            <DimensionBars
              dimensions={scoring_v2.dimensions}
              winnerIndex={
                (scoring_v2.overall_score?.product_a ?? 0) >=
                (scoring_v2.overall_score?.product_b ?? 0)
                  ? 0
                  : 1
              }
              testID="results-v2-bars"
            />
          </Animated.View>
        )}

        {/* 8. Score Breakdown (legacy — hidden when scoring_v2 present) */}
        {!scoring_v2 && scoring && (
          <Animated.View entering={FadeInDown.delay(800).duration(400)} style={styles.section}>
            <Text style={styles.sectionTitle}>{t('results.scores')}</Text>

            {(Object.keys(SCORE_LABELS) as (keyof ScoreBreakdown)[]).map((dim) => {
              const score0 = getProductScores(0)?.breakdown[dim] ?? 0;
              const score1 = getProductScores(1)?.breakdown[dim] ?? 0;

              return (
                <View key={dim} style={styles.scoreRow}>
                  <Text style={styles.scoreDimLabel}>{SCORE_LABELS[dim]}</Text>
                  <View style={styles.scoreBarsRow}>
                    {/* Product 0 bar (right aligned) */}
                    <View style={styles.scoreBarContainer}>
                      <View
                        style={[
                          styles.scoreBarFill,
                          styles.scoreBarLeft,
                          {
                            width: `${Math.min(score0, 100)}%`,
                            backgroundColor: getScoreColor(score0),
                          },
                        ]}
                      />
                    </View>
                    {/* Product 1 bar (left aligned) */}
                    <View style={styles.scoreBarContainer}>
                      <View
                        style={[
                          styles.scoreBarFill,
                          {
                            width: `${Math.min(score1, 100)}%`,
                            backgroundColor: getScoreColor(score1),
                          },
                        ]}
                      />
                    </View>
                  </View>
                </View>
              );
            })}

            {/* Legend */}
            <View style={styles.scoreLegend}>
              <Text style={styles.scoreLegendItem}>{products[0]?.name}</Text>
              <Text style={styles.scoreLegendItem}>{products[1]?.name}</Text>
            </View>

            {scoring.scoring_method && (
              <Text style={styles.scoringMethodText}>
                {scoring.scoring_method === 'personalized'
                  ? t('results.scoring.personalized')
                  : t('results.scoring.default')}
              </Text>
            )}
          </Animated.View>
        )}

        {/* 9. Feedback */}
        <FeedbackCard
          comparisonId={comparisonId}
          submitted={feedbackSubmitted}
          onSubmitted={() => setFeedbackSubmitted(true)}
        />

        {/* 10. Share action — Bundle E § Decision 6 pruned the "What's next?"
            CTA (broken NAVIGATE target) and the dead Save button. Share
            stays because the affordance has a working backend (handleShare
            → referral share sheet). Header already renders an icon-only
            share, but this labeled affordance below feedback gives users
            who scrolled past the header a second entry point. */}
        <View style={styles.actionsRow}>
          <TouchableOpacity style={styles.actionButton} onPress={handleShare}>
            <Share2 size={18} color={colors.accent} />
            <Text style={styles.actionButtonText}>{t('results.share')}</Text>
          </TouchableOpacity>
        </View>

        {/* Metadata */}
        {metadata && (
          <View style={styles.metadataSection}>
            <Text style={styles.metadataText}>
              {t('results.metadata.elapsed', { seconds: metadata.elapsed_seconds?.toFixed(1) ?? '0' })}
              {(metadata.cache_hits ?? 0) > 0
                ? t('results.metadata.cached', { count: metadata.cache_hits })
                : t('results.metadata.fresh')}
            </Text>
            {usageStatus && (
              <Text style={styles.metadataText}>
                {t('results.metadata.remainingDaily', { count: usageStatus.remaining.daily })}
              </Text>
            )}
          </View>
        )}
      </ScrollView>

      <DemographicsBottomSheet
        visible={demographicsVisible}
        onSubmit={handleDemographicsSubmit}
        onSkip={handleDemographicsSkip}
        errorMessage={demographicsError}
      />

      {/* F2.4 + F2.5: ShareBottomSheet + Loop 1 reward toast */}
      {sharableComparisonId ? (
        <ShareBottomSheet
          visible={shareSheetVisible}
          comparison={{
            id: sharableComparisonId,
            productA: products[0]?.name ?? '',
            productB: products[1]?.name ?? '',
            winnerName: winnerName ?? products[0]?.name ?? '',
          }}
          onClose={() => setShareSheetVisible(false)}
          onShared={handleShareCompleted}
          lifetimeRemaining={lifetimeRemaining ?? undefined}
        />
      ) : null}

      {loop1ToastVisible ? (
        <View style={styles.loop1Toast} accessibilityLiveRegion="polite">
          <Gift size={18} color={colors.bg.primary} />
          <View style={{ flex: 1 }}>
            <Text style={styles.loop1ToastTitle}>{t('referrals.loop1.toast')}</Text>
            {lifetimeRemaining !== null ? (
              <Text style={styles.loop1ToastSubtitle}>
                {t('referrals.loop1.counter', {
                  used: 3 - lifetimeRemaining,
                  total: 3,
                })}
              </Text>
            ) : null}
          </View>
        </View>
      ) : null}
    </View>
  );
}

/**
 * Phase 3 § 4b helpers — surface cohort match details inline on Results.
 * Backend already includes a `cohort_summary` block on the comparison
 * result when match quality is exact / broadened-governorate / broadened-
 * language (per CLAUDE.md cohort personalization invariant). When absent
 * or low-confidence, the helpers return values that make CohortBadge
 * render nothing (peerCount=0 OR governorate='').
 */
function resolveCohortPeerCount(result: ComparisonResult): number {
  const summary: any =
    (result as any)?.cohort_summary ??
    (result as any)?.personalization?.cohort ??
    null;
  if (!summary) return 0;
  const n = summary.peer_count ?? summary.peers_count ?? summary.peers ?? 0;
  return typeof n === 'number' ? Math.max(0, Math.floor(n)) : 0;
}

function resolveCohortGovernorate(result: ComparisonResult): string {
  const summary: any =
    (result as any)?.cohort_summary ??
    (result as any)?.personalization?.cohort ??
    null;
  if (!summary) return '';
  return typeof summary.governorate === 'string' ? summary.governorate : '';
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bg.primary,
  },
  emptyStateContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: spacing.xl,
  },
  loadingRingsContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: spacing.xl,
    gap: spacing.xl,
  },
  loadingRingsText: {
    ...typography.body,
    color: colors.text.secondary,
    textAlign: 'center',
    paddingHorizontal: spacing.xl,
  },
  emptyStateTitle: {
    ...typography.title,
    color: colors.text.primary,
    textAlign: 'center',
    marginBottom: spacing.sm,
  },
  emptyStateBody: {
    ...typography.body,
    color: colors.text.secondary,
    textAlign: 'center',
    marginBottom: spacing.lg,
  },
  emptyStateCta: {
    backgroundColor: colors.cta.primary,
    paddingHorizontal: spacing.xl,
    paddingVertical: spacing.md,
    borderRadius: radii.button,
  },
  emptyStateCtaText: {
    color: colors.cta.onPrimary,
    ...typography.bodyEmphasis,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingTop: 50,
    paddingBottom: spacing.md,
    paddingHorizontal: spacing.base,
    backgroundColor: colors.bg.primary,
    borderBottomWidth: 1,
    borderBottomColor: colors.border.light,
  },
  headerButton: {
    padding: spacing.sm,
  },
  headerTitle: {
    flex: 1,
    ...typography.body,
    fontWeight: '600',
    color: colors.text.primary,
    textAlign: 'center',
  },
  categorySwitchedBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    backgroundColor: colors.accentLight,
    padding: spacing.md,
    marginHorizontal: spacing.base,
    marginTop: spacing.sm,
    borderRadius: radii.button,
  },
  categorySwitchedText: {
    ...typography.caption,
    color: colors.accent,
  },
  scroll: {
    flex: 1,
  },
  scrollContent: {
    paddingBottom: spacing['3xl'],
  },

  // Product cards
  productsRow: {
    flexDirection: 'row',
    padding: spacing.base,
    gap: spacing.md,
  },
  productCard: {
    flex: 1,
  },
  // Bundle B/C/D Task 3.3 — wrapper exists only to anchor the
  // Reanimated transform; the actual card border/shadow stays on
  // .productCard so the visual style is unchanged at rest.
  productCardWrapper: {
    flex: 1,
  },
  bestPickBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'flex-start',
    gap: spacing.xs,
    backgroundColor: colors.accent,
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs,
    borderRadius: radii.chip,
    marginBottom: spacing.sm,
  },
  bestPickText: {
    ...typography.small,
    fontWeight: '700',
    color: '#FFF',
  },
  scoreBadge: {
    borderWidth: 2,
    borderRadius: spacing.sm,
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs,
    flexDirection: 'row',
    alignItems: 'baseline',
    alignSelf: 'flex-start',
    marginBottom: spacing.sm,
  },
  scoreBadgeValue: {
    fontSize: 20,
    fontWeight: '700',
  },
  scoreBadgeLabel: {
    ...typography.small,
    color: colors.text.secondary,
    marginStart: 1,
  },
  brandText: {
    ...typography.small,
    color: colors.text.secondary,
    marginBottom: 2,
  },
  productName: {
    ...typography.caption,
    fontWeight: '600',
    color: colors.text.primary,
    marginBottom: spacing.sm,
  },
  priceText: {
    ...typography.title,
    fontWeight: '700',
    color: colors.accent,
    marginBottom: 2,
  },
  priceUnavailable: {
    color: colors.text.secondary,
    fontSize: 14,
  },
  priceNote: {
    ...typography.small,
    color: colors.text.secondary,
    fontStyle: 'italic',
  },
  retailerText: {
    ...typography.small,
    color: colors.text.secondary,
    marginBottom: spacing.sm,
  },
  valueBadge: {
    alignSelf: 'flex-start',
    paddingHorizontal: spacing.sm,
    paddingVertical: 2,
    borderRadius: radii.chip,
    marginTop: spacing.xs,
    marginBottom: spacing.xs,
  },
  valueBadgeText: {
    ...typography.small,
    fontWeight: '600',
  },
  ratingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
    marginTop: spacing.sm,
  },
  ratingText: {
    ...typography.caption,
    fontWeight: '600',
    color: colors.text.primary,
  },
  reviewCountText: {
    ...typography.small,
    color: colors.text.secondary,
  },
  noRatingText: {
    ...typography.small,
    color: colors.text.secondary,
    fontStyle: 'italic',
    marginTop: spacing.sm,
  },
  bestForText: {
    ...typography.small,
    color: colors.text.secondary,
    fontStyle: 'italic',
    marginTop: spacing.xs,
  },

  // Confidence
  confidenceBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    marginHorizontal: spacing.base,
    marginBottom: spacing.sm,
    padding: spacing.md,
    backgroundColor: colors.bg.secondary,
    borderRadius: radii.button,
  },
  confidenceText: {
    ...typography.caption,
    fontWeight: '500',
  },

  // Sections
  section: {
    marginHorizontal: spacing.base,
    marginBottom: spacing.base,
    backgroundColor: colors.bg.secondary,
    borderRadius: radii.card,
    padding: spacing.base,
    borderWidth: 1,
    borderColor: colors.border.light,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  sectionTitle: {
    ...typography.body,
    fontWeight: '600',
    color: colors.text.primary,
    marginBottom: spacing.md,
  },
  verdictText: {
    ...typography.body,
    color: colors.text.secondary,
    lineHeight: 24,
  },
  tradeoffNote: {
    ...typography.caption,
    color: colors.text.secondary,
    fontStyle: 'italic',
    marginTop: spacing.sm,
  },
  /**
   * Cohort badge slot — sits between the "Why we picked this" verdict
   * block and the price section per design § 4b. CohortBadge guards
   * on missing data; when there's no cohort match the slot renders an
   * empty View, leaving the layout intact.
   */
  cohortBadgeSlot: {
    paddingHorizontal: spacing.lg,
    paddingBottom: spacing.md,
  },

  // Price comparison
  priceCompRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.border.light,
  },
  priceCompName: {
    ...typography.caption,
    color: colors.text.primary,
    flex: 1,
  },
  priceCompRight: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
  },
  priceCompAmount: {
    ...typography.body,
    fontWeight: '600',
    color: colors.text.primary,
  },
  priceLessBadge: {
    backgroundColor: colors.accentLight,
    paddingHorizontal: spacing.sm,
    paddingVertical: 2,
    borderRadius: radii.chip,
  },
  priceLessText: {
    ...typography.small,
    fontWeight: '600',
    color: colors.accent,
  },
  retailerAttribution: {
    ...typography.small,
    color: colors.text.secondary,
    marginTop: spacing.sm,
  },

  // Key differences / tradeoffs
  tradeoffRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.border.light,
  },
  tradeoffItem: {
    flex: 1,
    alignItems: 'center',
  },
  tradeoffProduct: {
    ...typography.caption,
    fontWeight: '600',
    color: colors.text.primary,
  },
  tradeoffDim: {
    ...typography.small,
    color: colors.text.secondary,
    marginTop: 2,
  },
  tradeoffVs: {
    ...typography.small,
    color: colors.text.secondary,
    marginHorizontal: spacing.sm,
  },
  differenceItem: {
    ...typography.caption,
    color: colors.text.secondary,
    marginBottom: spacing.sm,
    lineHeight: 20,
  },

  // Insights
  insightCard: {
    backgroundColor: colors.bg.primary,
    borderRadius: radii.button,
    padding: spacing.md,
    marginBottom: spacing.sm,
    borderStartWidth: 3,
    borderStartColor: colors.accent,
  },
  insightFocusArea: {
    ...typography.small,
    fontWeight: '600',
    color: colors.accent,
    textTransform: 'capitalize',
    marginBottom: spacing.xs,
  },
  insightText: {
    ...typography.caption,
    color: colors.text.secondary,
    lineHeight: 20,
  },

  // Specs
  diffToggleRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.md,
  },
  diffToggleLabel: {
    ...typography.caption,
    color: colors.text.secondary,
  },
  specsTable: {
    borderRadius: radii.button,
    overflow: 'hidden',
  },
  specsTableRow: {
    flexDirection: 'row',
    borderBottomWidth: 1,
    borderBottomColor: colors.border.light,
  },
  specsTableCell: {
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.sm,
  },
  specsKeyCell: {
    flex: 1,
    ...typography.small,
    color: colors.text.secondary,
    textTransform: 'capitalize',
  },
  specsValueCell: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
  },
  specsValueText: {
    ...typography.small,
    fontWeight: '500',
    color: colors.text.primary,
  },
  winnerDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: colors.accent,
  },

  // Reviews
  reviewCard: {
    marginBottom: spacing.sm,
  },
  reviewCardTitle: {
    ...typography.body,
    fontWeight: '600',
    color: colors.text.primary,
    marginBottom: spacing.sm,
  },
  sourceText: {
    ...typography.small,
    color: colors.accent,
    fontWeight: '500',
  },
  consensusText: {
    ...typography.caption,
    color: colors.text.secondary,
    lineHeight: 20,
    marginTop: spacing.sm,
    marginBottom: spacing.sm,
  },
  highlightsSection: {
    marginTop: spacing.sm,
  },
  highlightItem: {
    ...typography.caption,
    marginBottom: spacing.xs,
    marginStart: spacing.xs,
    lineHeight: 20,
  },
  dividedNote: {
    ...typography.small,
    color: colors.warning,
    fontStyle: 'italic',
    marginTop: spacing.sm,
  },

  // Scores
  scoreRow: {
    marginBottom: spacing.md,
  },
  scoreDimLabel: {
    ...typography.small,
    color: colors.text.secondary,
    marginBottom: spacing.xs,
  },
  scoreBarsRow: {
    flexDirection: 'row',
    gap: 2,
  },
  scoreBarContainer: {
    flex: 1,
    height: 8,
    backgroundColor: colors.border.light,
    borderRadius: 4,
    overflow: 'hidden',
  },
  scoreBarFill: {
    height: '100%',
    borderRadius: 4,
  },
  scoreBarLeft: {
    alignSelf: 'flex-end',
  },
  scoreLegend: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: spacing.sm,
  },
  scoreLegendItem: {
    ...typography.small,
    color: colors.text.secondary,
  },
  scoringMethodText: {
    ...typography.small,
    color: colors.text.secondary,
    textAlign: 'center',
    fontStyle: 'italic',
    marginTop: spacing.sm,
  },

  // Actions
  actionsRow: {
    flexDirection: 'row',
    gap: spacing.md,
    marginHorizontal: spacing.base,
    marginTop: spacing.sm,
    marginBottom: spacing.base,
  },
  actionButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.sm,
    paddingVertical: spacing.md,
    borderRadius: radii.button,
    borderWidth: 1,
    borderColor: colors.border.medium,
    backgroundColor: colors.bg.primary,
  },
  actionButtonText: {
    ...typography.body,
    fontWeight: '600',
    color: colors.text.primary,
  },

  // Metadata
  metadataSection: {
    paddingVertical: spacing.base,
    alignItems: 'center',
  },
  metadataText: {
    ...typography.small,
    color: colors.text.secondary,
  },
  // F2.4: Result-aware share CTA below verdict
  referralCta: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.sm,
    backgroundColor: colors.accent,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.lg,
    borderRadius: radii.button,
    minHeight: 48,
  },
  referralCtaText: {
    ...typography.body,
    fontWeight: '600',
    color: colors.bg.primary,
    flexShrink: 1,
  },
  // F2.5: Loop 1 toast — "your next comparison goes 2x deeper"
  loop1Toast: {
    position: 'absolute',
    bottom: spacing['2xl'],
    start: spacing.lg,
    end: spacing.lg,
    backgroundColor: colors.text.primary,
    borderRadius: radii.card,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.base,
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    ...shadows.card,
  },
  loop1ToastTitle: {
    ...typography.body,
    fontWeight: '600',
    color: colors.bg.primary,
  },
  loop1ToastSubtitle: {
    ...typography.small,
    color: colors.bg.primary,
    opacity: 0.8,
    marginTop: 2,
  },
});
