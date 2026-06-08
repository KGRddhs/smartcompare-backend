/**
 * Qaren - Results Screen (Single Scroll)
 * Converts 3-tab layout to single continuous scroll.
 * Preserves ALL business logic: SSE handling, event tracking, share, feedback.
 */
import React, { useState, useEffect, useRef } from 'react';
// Lane A-L3 Task L3.7 — wall-time instrumentation. ResultsScreen marks
// the 4 visual stages: first_card_visible, all_cards_visible,
// ready_celebration (winner reveal), user_tappable (post-reveal interactive).
// HomeScreen / SSE side marks ttfb. report() fires on unmount so partial
// journeys still surface in Sentry with whatever stages reached.
import { getWallTimeTracker } from '../lib/performance/wallTimeInstrumentation';
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
import { LoadingRings } from '../components/hero/LoadingRings';
import { HeroRings } from '../components/results/HeroRings';
import { DimensionBars } from '../components/results/DimensionBars';
import { TopMatchBadge } from '../components/results/TopMatchBadge';
import { ResultsContent } from '../components/results/ResultsContent';
import { RevealBurst } from '../components/hero/RevealBurst';
import { FactualVerdict } from '../components/results/FactualVerdict';
import { ConfidencePills } from '../components/results/ConfidencePills';
import { ConfidenceDetailsSheet } from '../components/results/ConfidenceDetailsSheet';
import { PersonalizationChip } from '../components/results/PersonalizationChip';
import { anyEstimated } from '../services/sourceMethod';
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
  // Bundle C § 5b — which leg's "What we know" sheet is currently open.
  // `null` keeps the sheet closed; tapping a pill sets the leg.
  const [sheetLeg, setSheetLeg] = useState<'price' | 'reviews' | 'specs' | null>(null);
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

  // Bucket A bug 2 — Camera capture path. ScanCamera passes a
  // vision_products: [uri0, uri1] array via React Nav; identifyFromImages
  // returns either action='comparison' (full ComparisonResult inline) or
  // action='need_second_product' / error. Same 1.2s min-display floor as
  // the history path so the LoadingRings hero animation lands.
  useEffect(() => {
    const visionProducts = route?.params?.vision_products;
    if (!visionProducts || visionProducts.length < 2 || result) return;

    let cancelled = false;
    (async () => {
      try {
        const { identifyFromImages } = await import('../services/api');
        const data: any = await identifyFromImages(visionProducts, 'bahrain');

        if (data?.action === 'comparison') {
          const remaining = minDisplayUntilRef.current - Date.now();
          if (remaining > 0) {
            await new Promise((resolve) => setTimeout(resolve, remaining));
          }
          if (!cancelled) {
            // /image/identify returns the comparison inline; the result body
            // may live at data.result or be the data object itself.
            setResult((data.result ?? data) as ComparisonResult);
            setLoadingResult(false);
          }
        } else if (data?.action === 'need_second_product') {
          if (!cancelled) {
            setLoadError('need_more_photos');
            setLoadingResult(false);
          }
        } else {
          if (!cancelled) {
            setLoadError('vision_failed');
            setLoadingResult(false);
          }
        }
      } catch (err: any) {
        if (cancelled) return;
        // H3: USAGE_LIMIT on the camera path routes to Paywall rather than
        // showing "Snap one more in better light" (which was the catch-all
        // misleading message — the user isn't holding the camera wrong,
        // they've hit their freemium cap).
        if (err?.code === 'USAGE_LIMIT') {
          setLoadingResult(false);
          navigation.navigate('Paywall', { initialUsage: err.detail ?? undefined });
          return;
        }
        setLoadError('vision_failed');
        setLoadingResult(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [route?.params?.vision_products, result, navigation]);

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

  // Lane A-L3 Task L3.7 — mark first/all-card visibility milestones as
  // soon as the result settles + loadingResult false transitions. Both
  // products are mounted simultaneously in the hero pair (`heroPair`
  // FlatList in ResultsContent), so the two stages collapse onto the
  // same React tick — but the *tag pair* lets the dashboard catch the
  // case where a future redesign staggers card paint (settle-window).
  useEffect(() => {
    if (loadingResult) return;
    if (!products || products.length < 2) return;
    const tracker = getWallTimeTracker();
    tracker.mark('first_card_visible');
    tracker.mark('all_cards_visible');
  }, [loadingResult, products?.length]);

  useEffect(() => {
    // Winner reveal with haptic feedback + Bundle B/C/D Task 3.3 spring.
    const tracker = getWallTimeTracker();
    const timer = setTimeout(async () => {
      setWinnerRevealed(true);
      winnerScale.value = withSpring(1, motion.springConfig.progress);
      // Lane A-L3 Task L3.7 — celebration fires; 3-part haptic on reveal.
      tracker.mark('ready_celebration');
      try {
        await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
      } catch {}
      // Spring is ~400ms; mark `user_tappable` after the spring settles
      // so the tag reflects "moment the user can actually interact"
      // rather than "moment the reveal began."
      setTimeout(() => tracker.mark('user_tappable'), 420);
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
      // Lane A-L3 Task L3.7 — report aggregate `comparison_wall_time` event
      // on unmount so partial journeys still surface stages reached. No-op
      // when start() was never called (e.g. history-detail entry, where
      // HomeScreen-side tracker.start() didn't fire).
      tracker.report();
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
            {route?.params?.vision_products
              ? t('results.loading.fromCamera')
              : t('results.loading.fromHistory')}
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
              : loadError === 'need_more_photos'
              ? t('results.emptyState.needMorePhotos')
              : loadError === 'vision_failed'
              ? t('results.emptyState.visionFailed')
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

  // Bundle E S3 — Lane A2 — orchestrator-side derivations for ResultsContent.
  const scoringV2WinnerIndex: 0 | 1 =
    (scoring_v2?.overall_score?.product_a ?? 0) >=
    (scoring_v2?.overall_score?.product_b ?? 0)
      ? 0
      : 1;
  const presentationWinnerIndex: 0 | 1 = (
    scoring_v2 ? scoringV2WinnerIndex : (winner_index === 1 ? 1 : 0)
  ) as 0 | 1;

  return (
    <View style={styles.container}>
      <ResultsContent
        result={result}
        products={products}
        winnerIndex={presentationWinnerIndex}
        scoring_v2={scoring_v2}
        comparisonId={comparisonId}
        cohortPeerCount={resolveCohortPeerCount(result)}
        cohortGovernorate={resolveCohortGovernorate(result)}
        isRTL={isRTL}
        feedbackSubmitted={feedbackSubmitted}
        onFeedbackSubmitted={() => setFeedbackSubmitted(true)}
        feedbackComparisonId={comparisonId}
        sheetLeg={sheetLeg}
        onPillPress={(leg) => setSheetLeg(leg)}
        onCloseSheet={() => setSheetLeg(null)}
        winnerRevealed={winnerRevealed}
        winnerScaleAnimStyle={winnerAnimStyle}
        onBack={() => navigation.goBack()}
        onShare={handleShare}
      />

      {/*
       * Bundle E S3 — DELETE list executed:
       *  - categorySwitchedBanner (per memory/feedback_no_info_banners.md)
       *  - duplicate header centered title (TopMatchBadge → header)
       *  - per-product scoreBadge + bestPickBadge (winner role → header)
       *  - standalone Reviews + Specs sections (folded into ResultsAccordion)
       *  - actions row second Share affordance (header is only one in JSX)
       *  - metadata footer
       *  - legacy Score Breakdown (now lives in ResultsContent fallback)
       *
       * Orchestrator-only surfaces (DemographicsBottomSheet,
       * ShareBottomSheet, Loop 1 toast) stay below — modal-style overlays.
       */}

      {/* legacy-stub: dead block retained as a no-op so the JSX tree close
          still parses cleanly under the orchestrator return path. */}

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
  // Bundle E S3 — orchestrator-only styles. Presentation styles live in
  // ResultsContent.tsx + ResultsAccordion.tsx. The 12 styles below are the
  // ones the orchestrator still uses for loading / empty-state / Loop 1 toast.
  container: {
    flex: 1,
    backgroundColor: colors.bg.primary,
  },
  // Loading branch — LoadingRings hero + caption.
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
  // Empty-state branch — not-found / need-more-photos / generic.
  emptyStateContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: spacing.xl,
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
  // Header — loading + empty-state branches reuse this row.
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingTop: 50,
    paddingBottom: spacing.sm,
    paddingHorizontal: spacing.base,
    backgroundColor: colors.bg.primary,
  },
  headerButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: colors.bg.secondary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  // F2.5 Loop 1 reward toast — bottom-pinned slide-in after Share completes.
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
