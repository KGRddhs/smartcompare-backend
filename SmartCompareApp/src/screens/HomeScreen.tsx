/**
 * Qaren - Home Screen (Bundle E S3 REWRITE).
 *
 * REWRITTEN top-down per docs/claude-design-handoff/ui_kits/mobile/
 * HomeScreen.jsx (1-717). Element order:
 *   1. Header        — QarenLogo + "Qaren" word + HeaderCounter pill
 *                      [JSX:674-683]
 *   2. Hero          — "Compare anything." 600/16 [JSX:685-691]
 *   3. CategoryStrip — horizontal scroll of 5 cats [JSX:693, 391-432]
 *   4. CompareCard   — [JSX:163-220]
 *        ModeSegment (pill container w/ 3 inner tabs) [JSX:111-160]
 *        Body (ScanBody | TwoInputShell) [JSX:179-197]
 *        Compare CTA (full-width black button at bottom) [JSX:199-217]
 *   5. SmartPickCard  [JSX:438-501]
 *   6. QuickCategories [JSX:534-570]
 *   7. SavingsBanner  [JSX:573-605]
 *   8. TrendingNearYou [JSX:608-651]
 *
 * DELETED from prior state:
 *   - home-editorial-stub 0-height marker (not in JSX)
 *   - the void-serverOnline plumbing (no health-state UI in JSX).
 *     healthCheck() retained as a fire-and-forget for telemetry — its
 *     return value is no longer threaded into state.
 *   - Per-chip border/borderColor on the 3 mode chips (the pill container
 *     now owns the outer border)
 *
 * Element-order checklist: docs/plans/_s3-a1-element-order.md
 */

import React, { useState, useCallback, useRef, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  SafeAreaView,
  ScrollView,
  Alert,
} from 'react-native';
import { CameraView, useCameraPermissions } from 'expo-camera';
import * as ImagePicker from 'expo-image-picker';
import * as Haptics from 'expo-haptics';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withSpring,
} from 'react-native-reanimated';
import { motion } from '../theme/motion';
import { Camera } from 'lucide-react-native';
import { ScanIcon, LinkIcon, TypeIcon } from '../icons';
import { useTranslation } from 'react-i18next';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useFocusEffect } from '@react-navigation/native';
import AsyncStorage from '@react-native-async-storage/async-storage';

import { colors, spacing, radii, typography } from '../theme';
import { RootStackParamList } from '../types';
import {
  healthCheck,
  streamComparison,
  parseApiError,
  trackEvent,
} from '../services/api';
import api from '../services/api';
import { getSavedUser, User } from '../services/authService';
import { isUsageLimitError, getUsageLimitDetail } from '../services/usageService';
import CategorySelector from '../components/CategorySelector';
import QarenLogo from '../components/QarenLogo';
import TwoInputShell from '../components/TwoInputShell';
import PaywallBanner from '../components/PaywallBanner';
import HomeEditorialSections from '../components/HomeEditorialSections';
import { LoadingScreenVariants } from './LoadingScreenVariants';
import { useComparisonCounter } from '../hooks/useComparisonCounter';
import { getReferralStatus } from '../services/referralService';
// Lane A-L3 Task L3.7 — wall-time instrumentation. Tracker starts on
// Compare tap, marks `ttfb` on first SSE event; ResultsScreen continues
// through `first_card_visible` / `all_cards_visible` / `ready_celebration`
// / `user_tappable`. Aggregated info-level Sentry event surfaces in the
// dashboard for the 88s wall-time gap diagnosis.
import { getWallTimeTracker } from '../lib/performance/wallTimeInstrumentation';

const RECENT_SEARCHES_KEY = '@qaren_recent_searches';
const MAX_RECENT = 5;
// Bundle B/C/D — exactly 2 products per comparison.
export const MAX_IMAGES = 2;

type HomeScreenProps = {
  navigation: NativeStackNavigationProp<RootStackParamList, 'Home'>;
  onLogout?: () => void;
};

type InputMode = 'scan' | 'url' | 'type';

export default function HomeScreen({ navigation }: HomeScreenProps) {
  const { t } = useTranslation();
  const [, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState('');

  const [permission, requestPermission] = useCameraPermissions();
  const [, setRecentSearches] = useState<string[]>([]);
  const recentSearchesRef = useRef<string[]>([]);

  const [inputMode, setInputMode] = useState<InputMode>('scan');
  const [selectedCategory, setSelectedCategory] = useState<string>('electronics');
  const abortRef = useRef<(() => void) | null>(null);

  const { used, total, canCompare, increment } = useComparisonCounter();

  const [bonusInfo, setBonusInfo] = useState<{
    bonusRemaining: number;
    referrerName?: string;
    expiresAt?: Date;
  }>({ bonusRemaining: 0 });

  // Analytics session flags — toggled by TwoInputShell callbacks, read on
  // submit, reset after each submit.
  const pasteSplitUsedRef = useRef(false);
  const autoswitchUsedRef = useRef(false);
  const lastViewedModeRef = useRef<InputMode | null>(null);
  const prevCanCompareRef = useRef<boolean>(canCompare);

  useFocusEffect(
    useCallback(() => {
      let cancelled = false;
      (async () => {
        try {
          const status: any = await getReferralStatus();
          if (cancelled) return;
          const bonusRemaining: number = Number(status?.monthly_bonus_comparisons ?? 0);
          const referrerName: string | undefined =
            typeof status?.bonus_referrer_name === 'string'
              ? status.bonus_referrer_name
              : undefined;
          const rawExpiry =
            status?.bonus_expires_at ?? status?.next_bonus_expires_at ?? null;
          const expiresAt: Date | undefined =
            rawExpiry ? new Date(rawExpiry) : undefined;
          setBonusInfo({ bonusRemaining, referrerName, expiresAt });
        } catch {
          /* fire-and-forget */
        }
      })();
      return () => {
        cancelled = true;
      };
    }, [])
  );

  // Min-display floor (1.2s) for Home→Results transitions per design § 3.
  // advanceTimerRef captures the pending setTimeout handle so we can
  // cancel the navigation if the user leaves the screen (unmount) OR
  // the compare aborts on error before the floor expires.
  const loadingStartedAtRef = useRef<number | null>(null);
  const advanceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const MIN_LOADING_MS = 1200;
  const navigateToResultsWithFloor = useCallback(
    (result: any) => {
      const startedAt = loadingStartedAtRef.current ?? Date.now();
      const elapsed = Date.now() - startedAt;
      const remaining = Math.max(0, MIN_LOADING_MS - elapsed);
      const advance = () => {
        advanceTimerRef.current = null;
        loadingStartedAtRef.current = null;
        navigation.navigate('Results' as any, { result });
        // setLoading(false) fires AFTER navigate so the theatrical
        // loader stays mounted until the user is on the Results screen.
        // On cached/fast paths setLoading(false) at the caller would
        // unmount LoadingScreenVariants BEFORE the floor timer fires,
        // exposing bare HomeScreen for up to 1.2s.
        setLoading(false);
      };
      if (remaining === 0) advance();
      else advanceTimerRef.current = setTimeout(advance, remaining);
    },
    [navigation]
  );

  // Clear any pending floor timer on unmount so navigate-after-unmount
  // can never fire (Gate B #1). Error paths cancel inline.
  useEffect(() => {
    return () => {
      if (advanceTimerRef.current) {
        clearTimeout(advanceTimerRef.current);
        advanceTimerRef.current = null;
      }
    };
  }, []);

  useFocusEffect(
    useCallback(() => {
      checkServer();
      loadUser();
      loadRecentSearches();
    }, [])
  );

  const loadUser = async () => {
    const savedUser = await getSavedUser();
    setUser(savedUser);
  };

  // Fire-and-forget health check — no longer surfaced in UI per S3
  // (JSX has no health-state indicator). Kept as telemetry.
  const checkServer = async () => {
    try {
      await healthCheck();
    } catch {
      /* fire-and-forget */
    }
  };

  const loadRecentSearches = async () => {
    try {
      const stored = await AsyncStorage.getItem(RECENT_SEARCHES_KEY);
      if (stored) {
        const parsed = JSON.parse(stored) as string[];
        setRecentSearches(parsed);
        recentSearchesRef.current = parsed;
      }
    } catch {
      /* no-op */
    }
  };

  const saveRecentSearch = async (query: string) => {
    const updated = [
      query,
      ...recentSearchesRef.current.filter((s) => s !== query),
    ].slice(0, MAX_RECENT);
    recentSearchesRef.current = updated;
    setRecentSearches(updated);
    await AsyncStorage.setItem(RECENT_SEARCHES_KEY, JSON.stringify(updated));
  };

  // --- Analytics ---

  useEffect(() => {
    if (lastViewedModeRef.current !== inputMode) {
      lastViewedModeRef.current = inputMode;
      trackEvent('compare_entry_view', { mode: inputMode });
    }
  }, [inputMode]);

  useEffect(() => {
    if (prevCanCompareRef.current && !canCompare) {
      trackEvent('compare_entry_paywall_banner_view', { mode: inputMode });
    }
    prevCanCompareRef.current = canCompare;
  }, [canCompare, inputMode]);

  const handleContentUnavailable = useCallback(
    (mode: 'text' | 'url' | 'scan', layer: string) => {
      trackEvent('compare_entry_content_block', { mode, layer });
      Alert.alert(
        t('home.compare.unavailable_title'),
        t('home.compare.unavailable_body')
      );
    },
    [t]
  );

  // --- Text comparison (SSE streaming, dual-shape pair) ---

  const handleTextCompare = (a: string, b: string) => {
    const productA = a.trim();
    const productB = b.trim();
    if (!productA || !productB) return;
    if (!canCompare) {
      navigation.navigate('Paywall');
      return;
    }

    saveRecentSearch(`${productA} vs ${productB}`);
    setLoading(true);
    setStatusMessage(t('results.loading.finding'));
    loadingStartedAtRef.current = Date.now();
    let navigated = false;
    // Lane A-L3 Task L3.7 — start wall-time tracker at the user's
    // Compare tap. Subsequent stages (`ttfb`, `first_card_visible`,
    // `all_cards_visible`, `ready_celebration`, `user_tappable`) get
    // marked across HomeScreen + ResultsScreen.
    const wallTime = getWallTimeTracker();
    wallTime.start();
    let ttfbMarked = false;
    const markTtfb = () => {
      if (!ttfbMarked) {
        ttfbMarked = true;
        wallTime.mark('ttfb');
      }
    };

    trackEvent('compare_entry_submit', {
      mode: 'text',
      used_paste_split: pasteSplitUsedRef.current,
      used_autoswitch: autoswitchUsedRef.current,
    });
    pasteSplitUsedRef.current = false;
    autoswitchUsedRef.current = false;

    const { subscribe, abort } = streamComparison(
      { product_a: productA, product_b: productB },
      { selected_category: selectedCategory }
    );
    abortRef.current = abort;

    subscribe({
      onStatus: (message) => {
        markTtfb();
        setStatusMessage(typeof message === 'string' ? message : String(message));
      },
      onSpecs: () => markTtfb(),
      onPrices: () => markTtfb(),
      onComplete: async (data) => {
        markTtfb();
        abortRef.current = null;
        setStatusMessage('');
        if (!navigated && data.success) {
          navigated = true;
          await increment();
          // Loader stays mounted until navigateToResultsWithFloor's
          // `advance` closure calls setLoading(false) AFTER navigate.
          // See navigateToResultsWithFloor comment above for rationale.
          navigateToResultsWithFloor(data);
        } else if (!data.success) {
          // Backend reported success=false — never queue a floor nav.
          if (advanceTimerRef.current) {
            clearTimeout(advanceTimerRef.current);
            advanceTimerRef.current = null;
          }
          setLoading(false);
          // Genuine-BH bundle (D2) — a timeout hard-fail surfaces the soft
          // results-still-settling copy, never the backend `error` string
          // (which may carry forbidden vocab). Other failures keep the
          // existing sharper-match nudge.
          const isTimeout = data.code === 'TIMEOUT' || data.code === 'STREAM_TIMEOUT';
          Alert.alert(
            t('common.error'),
            isTimeout ? t('home.errors.timeout') : data.error || t('home.errors.comparison')
          );
        }
      },
      onError: (error: any) => {
        abortRef.current = null;
        // Cancel any pending floor timer so a failed compare can never
        // silently navigate to Results after the 1.2s floor expires.
        if (advanceTimerRef.current) {
          clearTimeout(advanceTimerRef.current);
          advanceTimerRef.current = null;
        }
        setLoading(false);
        setStatusMessage('');
        const parsed = parseApiError(error);
        if (parsed.code === 'CONTENT_UNAVAILABLE') {
          const layer = error?.response?.data?.layer ?? 'unknown';
          handleContentUnavailable('text', layer);
          return;
        }
        if (isUsageLimitError(error)) {
          const detail = getUsageLimitDetail(error);
          navigation.navigate('Paywall', { initialUsage: detail ?? undefined });
          return;
        }
        // Genuine-BH bundle (D2) — transient timeout (HTTP 503 / code TIMEOUT,
        // normalized by parseApiError). Show the soft still-gathering-prices
        // copy with the implicit tap-to-retry; NEVER the backend error string
        // or scary failure copy. parseApiError returns an empty message for
        // this code precisely so it can never leak into the UI.
        if (parsed.code === 'TIMEOUT') {
          Alert.alert(t('common.error'), t('home.errors.timeout'));
          return;
        }
        Alert.alert(t('common.error'), error.message || t('home.errors.comparison'));
      },
    });
  };

  // --- URL comparison ---

  const handleUrlCompare = async (urlA: string, urlB: string) => {
    const url1 = urlA.trim();
    const url2 = urlB.trim();
    if (!url1 || !url2) return;
    if (!canCompare) {
      navigation.navigate('Paywall');
      return;
    }

    trackEvent('compare_entry_submit', {
      mode: 'url',
      used_paste_split: pasteSplitUsedRef.current,
      used_autoswitch: autoswitchUsedRef.current,
    });
    pasteSplitUsedRef.current = false;
    autoswitchUsedRef.current = false;

    setLoading(true);
    loadingStartedAtRef.current = Date.now();
    try {
      const response = await api.post('/api/v1/url/compare', {
        url1,
        url2,
        region: 'bahrain',
        selected_category: selectedCategory,
      });
      if (response.data.success) {
        await increment();
        // Loader stays mounted until navigateToResultsWithFloor's
        // `advance` closure calls setLoading(false) AFTER navigate.
        navigateToResultsWithFloor(response.data);
      } else {
        // Backend reported success=false — drop loader immediately.
        setLoading(false);
        Alert.alert(t('common.error'), response.data.error || t('home.errors.comparison'));
      }
    } catch (error: any) {
      // Cancel any pending floor timer so a failed URL compare can
      // never silently navigate to Results after the 1.2s floor expires.
      if (advanceTimerRef.current) {
        clearTimeout(advanceTimerRef.current);
        advanceTimerRef.current = null;
      }
      // Drop loader immediately on error — errors should never wait the
      // theatrical floor.
      setLoading(false);
      const parsed = parseApiError(error);
      if (parsed.code === 'CONTENT_UNAVAILABLE') {
        const layer = error?.response?.data?.layer ?? 'unknown';
        handleContentUnavailable('url', layer);
      } else if (isUsageLimitError(error)) {
        const detail = getUsageLimitDetail(error);
        navigation.navigate('Paywall', { initialUsage: detail ?? undefined });
      } else if (parsed.code === 'TIMEOUT') {
        // Genuine-BH bundle (D2) — soft timeout copy, never the backend string.
        Alert.alert(t('common.error'), t('home.errors.timeout'));
      } else {
        Alert.alert(t('common.error'), parsed.message);
      }
    }
  };

  const handleModeChange = (mode: InputMode) => {
    if (!canCompare) {
      if (mode !== inputMode) setInputMode(mode);
      trackEvent('compare_entry_paywall_banner_view', { mode });
      navigation.navigate('Paywall');
      return;
    }
    setInputMode(mode);
  };

  const pickFromGalleryFallback = async () => {
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsMultipleSelection: true,
      selectionLimit: MAX_IMAGES,
      quality: 0.8,
      exif: false,
    });
    if (!result.canceled && result.assets && result.assets.length >= MAX_IMAGES) {
      navigation.navigate('ScanCamera');
    }
  };

  const cameraPermissionGranted = permission?.granted;

  // Compare CTA gate: scan-only on HomeScreen. Type/Link modes consolidate
  // the Compare button INSIDE TwoInputShell (single source of truth — the
  // shell already owns the bothValid gate + celebration). The HomeScreen
  // CTA below renders ONLY in scan mode where its label is "Open camera"
  // and TwoInputShell is not on screen. The conditional render gate at
  // the JSX site (`canCompare && inputMode === 'scan' &&`) is the single
  // truth — no separate flag needed.
  const handleScanCtaPress = () => {
    navigation.navigate('ScanCamera');
  };

  const scanCtaLabel = t('home.cta.openCamera', {
    defaultValue: 'Open camera',
  });

  const renderCenterArea = () => {
    if (!canCompare) {
      return (
        <PaywallBanner
          onSeeOptions={() => {
            trackEvent('compare_entry_paywall_banner_tap', { mode: inputMode });
            navigation.navigate('Paywall');
          }}
        />
      );
    }

    if (inputMode === 'scan') {
      if (!cameraPermissionGranted) {
        return (
          <View style={styles.permissionCard}>
            <Camera size={48} color={colors.text.secondary} />
            <Text style={styles.permissionTitle}>{t('home.permission.title')}</Text>
            <Text style={styles.permissionText}>{t('home.permission.body')}</Text>
            <TouchableOpacity style={styles.permissionButton} onPress={requestPermission}>
              <Text style={styles.permissionButtonText}>
                {t('home.permission.cta')}
              </Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.galleryFallback} onPress={pickFromGalleryFallback}>
              <Text style={styles.galleryFallbackText}>
                {t('home.permission.gallery_link')}
              </Text>
            </TouchableOpacity>
          </View>
        );
      }
      // JSX-aligned ScanBody preview pattern per HomeScreen.jsx:222-265.
      const goToScan = () => navigation.navigate('ScanCamera');
      return (
        <View testID="home-scan-preview" style={styles.scanPreview}>
          <TouchableOpacity
            testID="home-scan-preview-row-a"
            style={styles.scanPreviewRow}
            onPress={goToScan}
            accessibilityRole="button"
            accessibilityLabel={t('home.scan.preview.row_a', {
              defaultValue: 'Tap to snap product A',
            })}
            activeOpacity={0.7}
          >
            <View style={styles.scanPreviewNumeral}>
              <Text style={styles.scanPreviewNumeralText}>1</Text>
            </View>
            <View style={styles.scanPreviewPlaceholder}>
              <Camera size={28} color={colors.text.secondary} strokeWidth={2} />
              <Text style={styles.scanPreviewPlaceholderTitle} numberOfLines={1}>
                {t('home.scan.preview.tap', { defaultValue: 'Tap to snap' })}
              </Text>
              <Text style={styles.scanPreviewPlaceholderSub} numberOfLines={1}>
                {t('home.scan.preview.product_a', { defaultValue: 'Product A' })}
              </Text>
            </View>
          </TouchableOpacity>

          <View style={styles.scanPreviewDivider} pointerEvents="none">
            <View style={styles.scanPreviewHairline} />
            <View style={styles.scanPreviewVsPill}>
              <Text style={styles.scanPreviewVsText}>VS</Text>
            </View>
          </View>

          <TouchableOpacity
            testID="home-scan-preview-row-b"
            style={styles.scanPreviewRow}
            onPress={goToScan}
            accessibilityRole="button"
            accessibilityLabel={t('home.scan.preview.row_b', {
              defaultValue: 'Tap to snap product B',
            })}
            activeOpacity={0.7}
          >
            <View style={styles.scanPreviewNumeral}>
              <Text style={styles.scanPreviewNumeralText}>2</Text>
            </View>
            <View style={styles.scanPreviewPlaceholder}>
              <Camera size={28} color={colors.text.secondary} strokeWidth={2} />
              <Text style={styles.scanPreviewPlaceholderTitle} numberOfLines={1}>
                {t('home.scan.preview.tap', { defaultValue: 'Tap to snap' })}
              </Text>
              <Text style={styles.scanPreviewPlaceholderSub} numberOfLines={1}>
                {t('home.scan.preview.product_b', { defaultValue: 'Product B' })}
              </Text>
            </View>
          </TouchableOpacity>

          <Text style={styles.scanPreviewHint}>
            {t('home.scan.preview.hint', {
              defaultValue:
                'Center each product in the brackets — sharper match every time.',
            })}
          </Text>
        </View>
      );
    }

    // Text + URL modes both render through TwoInputShell. The shell owns
    // its own per-field input state AND its own Compare CTA — the
    // HomeScreen CTA is hidden in these modes (single source of truth
    // for the Compare action lives in the shell).
    return (
      <TwoInputShell
        mode={inputMode === 'url' ? 'url' : 'text'}
        disabled={loading}
        onSubmit={(a, b) => {
          if (inputMode === 'url') handleUrlCompare(a, b);
          else handleTextCompare(a, b);
        }}
        onPasteSplit={(sourceBox) => {
          pasteSplitUsedRef.current = true;
          trackEvent('compare_entry_paste_split', {
            source_box: sourceBox,
            mode: inputMode === 'url' ? 'url' : 'text',
          });
        }}
        onModeAutoswitch={(from, to) => {
          autoswitchUsedRef.current = true;
          setInputMode('url');
          trackEvent('compare_entry_mode_autoswitch', {
            from,
            to,
            trigger: 'url_paste',
          });
        }}
        onReady={(timeToReadyMs) => {
          trackEvent('compare_entry_ready', {
            mode: inputMode === 'url' ? 'url' : 'text',
            time_to_ready_ms: timeToReadyMs,
          });
        }}
      />
    );
  };

  const baseFreeRemaining = Math.max(0, total - used);
  const isLastFree = baseFreeRemaining === 1;
  const handleHeaderCounterPress = () => {
    trackEvent('compare_entry_paywall_banner_tap', { mode: inputMode });
    navigation.navigate('Paywall');
  };

  return (
    <SafeAreaView style={styles.container}>
      {/* 1. Header — Q logo + Qaren wordmark + HeaderCounter pill */}
      <View style={styles.header}>
        <View style={styles.headerLeft}>
          <QarenLogo size={28} />
          <Text style={[styles.logo, styles.logoSpaced]}>{t('app.name')}</Text>
        </View>
        {canCompare && (
          <TouchableOpacity
            testID="home-header-counter"
            onPress={handleHeaderCounterPress}
            accessibilityRole="button"
            accessibilityLabel={t('home.headerCounter.a11y', {
              free: baseFreeRemaining,
              total,
              bonus: bonusInfo.bonusRemaining,
            })}
            style={[
              styles.headerCounter,
              isLastFree && styles.headerCounterLast,
            ]}
          >
            <Text
              style={[
                styles.headerCounterText,
                isLastFree && styles.headerCounterTextLast,
              ]}
            >
              {baseFreeRemaining}/{total} {t('home.headerCounter.free')}
            </Text>
            {bonusInfo.bonusRemaining > 0 && (
              <>
                <Text
                  style={[
                    styles.headerCounterDot,
                    isLastFree && styles.headerCounterTextLast,
                  ]}
                  accessibilityElementsHidden
                  importantForAccessibility="no"
                >
                  {' · '}
                </Text>
                <Text
                  style={[
                    styles.headerCounterText,
                    isLastFree && styles.headerCounterTextLast,
                  ]}
                >
                  +{bonusInfo.bonusRemaining}
                </Text>
              </>
            )}
          </TouchableOpacity>
        )}
      </View>

      {/* 2. Hero copy "Compare anything." */}
      {canCompare && <Text style={styles.hero}>{t('home.hero')}</Text>}

      {/* 3. CategoryStrip */}
      {canCompare && (
        <CategorySelector
          value={selectedCategory}
          onChange={setSelectedCategory}
        />
      )}

      {/* Outer scroll wraps CompareCard + 4 editorial sections per JSX:695. */}
      <ScrollView
        testID="home-main-scroll"
        style={styles.mainScroll}
        contentContainerStyle={styles.mainScrollContent}
        showsVerticalScrollIndicator={false}
        keyboardShouldPersistTaps="handled"
      >
        {/* 4. CompareCard — ModeSegment + Body + Compare CTA */}
        <View
          style={[
            styles.compareCard,
            !canCompare && styles.compareCardPaywall,
          ]}
        >
          {/* ModeSegment — pill container w/ 3 inner tabs [JSX:111-160] */}
          <View
            style={[
              styles.modeSegment,
              !canCompare && { opacity: 0.5 },
            ]}
            accessibilityRole="tablist"
          >
            <ModeTab
              testID="home-mode-scan"
              label={t('home.mode.scan')}
              icon={
                <ScanIcon
                  size={14}
                  color={inputMode === 'scan' ? colors.cta.onPrimary : colors.text.secondary}
                />
              }
              active={inputMode === 'scan'}
              onPress={() => handleModeChange('scan')}
            />
            <ModeTab
              testID="home-mode-link"
              label={t('home.mode.link')}
              icon={
                <LinkIcon
                  size={14}
                  color={inputMode === 'url' ? colors.cta.onPrimary : colors.text.secondary}
                />
              }
              active={inputMode === 'url'}
              onPress={() => handleModeChange('url')}
            />
            <ModeTab
              testID="home-mode-type"
              label={t('home.mode.type')}
              icon={
                <TypeIcon
                  size={14}
                  color={inputMode === 'type' ? colors.cta.onPrimary : colors.text.secondary}
                />
              }
              active={inputMode === 'type'}
              onPress={() => handleModeChange('type')}
            />
          </View>

          {/* Center area — ScanBody | TwoInputShell | PaywallBanner */}
          <View style={styles.centerArea} testID="home-center-area">
            {renderCenterArea()}
          </View>

          {/* Compare CTA — scan-mode only. In link/type modes the CTA is
              consolidated INSIDE TwoInputShell (single source of truth).
              In scan mode the label flips to "Open camera" and routes
              straight to the ScanCamera screen. Hidden during paywall
              takeover (PaywallBanner has its own CTA). */}
          {canCompare && inputMode === 'scan' && (
            <TouchableOpacity
              testID="home-compare-cta"
              onPress={handleScanCtaPress}
              accessibilityRole="button"
              accessibilityLabel={scanCtaLabel}
              accessibilityState={{ disabled: false }}
              style={styles.compareCta}
            >
              <Text style={styles.compareCtaText}>{scanCtaLabel}</Text>
            </TouchableOpacity>
          )}
        </View>

        {/* 5-8. Editorial sections — JSX flat-sibling order (no internal
            ScrollView; the wrapper renders a View now). */}
        {canCompare && (
          <HomeEditorialSections
            onPressVerdict={(comparisonId) =>
              navigation.navigate('Results' as any, { from_history: comparisonId } as any)
            }
            onPickCategory={(cat) => {
              setSelectedCategory(cat as any);
              handleModeChange('type');
            }}
            onPressTrending={() => {
              handleModeChange('type');
            }}
          />
        )}
      </ScrollView>

      {/* Theatrical loading screen — replaces the prior small toast at
          the bottom of Home. Renders edge-to-edge so the brand moment
          (LoadingRings + caption) lands cleanly. The min-display floor
          (1.2s) is owned by navigateToResultsWithFloor on Home, so the
          inner LoadingScreenVariants runs in "comparison" mode (no
          additional floor) and the outer navigation queue keeps the
          screen visible until the floor + backend resolve. */}
      {loading ? (
        <View style={styles.loadingFullscreen} pointerEvents="auto">
          <LoadingScreenVariants
            variant="concentric"
            mode="comparison"
            caption={statusMessage || t('results.loading.finding')}
            testID="home-loading-screen"
          />
        </View>
      ) : null}
    </SafeAreaView>
  );
}

/**
 * Pill-container inner tab (S3 REWRITE).
 *
 * JSX:131-157 — flex:1 inner pill, borderRadius 999, no own border (the
 * outer ModeSegment owns the border). Black fill when active.
 */
interface ModeTabProps {
  testID: string;
  label: string;
  icon: React.ReactNode;
  active: boolean;
  onPress: () => void;
}

function ModeTab({ testID, label, icon, active, onPress }: ModeTabProps) {
  const scale = useSharedValue(active ? 1 : 0.96);

  React.useEffect(() => {
    scale.value = withSpring(active ? 1 : 0.96, motion.springConfig.chip);
  }, [active, scale]);

  const animStyle = useAnimatedStyle(() => ({
    transform: [{ scale: scale.value }],
  }));

  const handlePress = () => {
    try {
      const maybePromise = Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
      if (maybePromise && typeof maybePromise.catch === 'function') {
        maybePromise.catch(() => {});
      }
    } catch {
      /* no-op */
    }
    onPress();
  };

  return (
    <Animated.View style={[styles.modeTabHost, animStyle]}>
      <TouchableOpacity
        testID={testID}
        onPress={handlePress}
        accessibilityRole="button"
        accessibilityState={{ selected: active }}
        style={[styles.modeTab, active && styles.modeTabActive]}
      >
        {icon}
        <Text style={[styles.modeTabText, active && styles.modeTabTextActive]}>
          {label}
        </Text>
      </TouchableOpacity>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bg.primary,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.sm,
    paddingBottom: spacing.xs,
  },
  headerLeft: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  logo: {
    ...typography.title,
    fontWeight: '700',
    color: colors.text.primary,
  },
  logoSpaced: {
    marginStart: spacing.sm,
  },
  headerCounter: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: spacing.md,
    height: 28,
    borderRadius: radii.chip,
    backgroundColor: colors.bg.secondary,
    borderWidth: 1,
    borderColor: colors.border.light,
  },
  headerCounterLast: {
    backgroundColor: colors.accentLight,
    borderColor: colors.accent,
  },
  headerCounterText: {
    ...typography.caption,
    fontWeight: '600',
    color: colors.text.secondary,
    fontVariant: ['tabular-nums'],
  },
  headerCounterTextLast: {
    color: colors.accentDark,
  },
  headerCounterDot: {
    ...typography.caption,
    fontWeight: '600',
    color: colors.text.secondary,
    opacity: 0.5,
  },
  hero: {
    ...typography.body,
    fontWeight: '600',
    color: colors.text.primary,
    paddingHorizontal: spacing.lg,
    paddingBottom: spacing.sm,
  },
  // S3 — outer scroll hosts CompareCard + editorial sections.
  mainScroll: {
    flex: 1,
  },
  mainScrollContent: {
    paddingBottom: spacing['3xl'],
  },
  // CompareCard wraps ModeSegment + Body + Compare CTA per JSX:163-220.
  compareCard: {
    marginHorizontal: spacing.lg,
    marginTop: spacing.sm,
    padding: spacing.base,
    backgroundColor: colors.bg.secondary,
    borderRadius: radii.card,
    borderWidth: 1,
    borderColor: colors.border.light,
  },
  compareCardPaywall: {
    backgroundColor: 'transparent',
    borderColor: 'transparent',
  },
  centerArea: {
    marginTop: spacing.md,
  },
  // S3 REWRITE — ModeSegment pill container [JSX:111-160].
  // ONE outer container w/ borderRadius 999 + 1px border + padding 4 +
  // 4px gap. Each inner tab borrows the container's border (none of its
  // own). Active tab gets cta.primary fill + onPrimary text.
  modeSegment: {
    flexDirection: 'row',
    padding: 4,
    gap: 4,
    backgroundColor: colors.bg.primary,
    borderWidth: 1,
    borderColor: colors.border.light,
    borderRadius: 999,
  },
  modeTabHost: {
    flex: 1,
  },
  modeTab: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    gap: spacing.xs,
    paddingHorizontal: spacing.md,
    minHeight: 36,
    borderRadius: 999,
    backgroundColor: 'transparent',
  },
  modeTabActive: {
    backgroundColor: colors.cta.primary,
  },
  modeTabText: {
    ...typography.caption,
    color: colors.text.secondary,
    fontWeight: '500',
  },
  modeTabTextActive: {
    color: colors.cta.onPrimary,
    fontWeight: '600',
  },
  // S3 REWRITE — Compare CTA [JSX:199-217]. Full-width, 48px tall,
  // cta.primary background, cta.onPrimary text. Disabled state at 0.5.
  compareCta: {
    marginTop: spacing.lg,
    height: 48,
    borderRadius: radii.button,
    backgroundColor: colors.cta.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  compareCtaText: {
    ...typography.body,
    fontWeight: '600',
    color: colors.cta.onPrimary,
  },
  // Scan preview pattern — unchanged from prior state, JSX:222-265.
  scanPreview: {
    flexDirection: 'column',
    gap: 12,
    paddingVertical: spacing.sm,
  },
  scanPreviewRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  scanPreviewNumeral: {
    width: 22,
    height: 22,
    borderRadius: 11,
    backgroundColor: colors.bg.secondary,
    borderWidth: 1,
    borderColor: colors.border.medium,
    alignItems: 'center',
    justifyContent: 'center',
  },
  scanPreviewNumeralText: {
    fontSize: 12,
    fontWeight: '700',
    lineHeight: 12,
    color: colors.text.secondary,
  },
  scanPreviewPlaceholder: {
    flex: 1,
    minHeight: 76,
    borderRadius: radii.card,
    backgroundColor: colors.bg.primary,
    borderWidth: 1,
    borderColor: colors.border.medium,
    borderStyle: 'dashed',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 4,
    paddingHorizontal: 16,
    paddingVertical: 12,
  },
  scanPreviewPlaceholderTitle: {
    fontSize: 14,
    fontWeight: '500',
    lineHeight: 14 * 1.3,
    color: colors.text.primary,
  },
  scanPreviewPlaceholderSub: {
    fontSize: 12,
    fontWeight: '400',
    lineHeight: 12 * 1.4,
    color: colors.text.secondary,
  },
  scanPreviewDivider: {
    height: 6,
    position: 'relative',
  },
  scanPreviewHairline: {
    position: 'absolute',
    left: 11,
    top: -6,
    bottom: -6,
    width: 1,
    backgroundColor: colors.border.light,
  },
  scanPreviewVsPill: {
    position: 'absolute',
    left: 20,
    top: -8,
    height: 22,
    paddingHorizontal: 10,
    borderRadius: 999,
    backgroundColor: colors.accentLight,
    alignItems: 'center',
    justifyContent: 'center',
  },
  scanPreviewVsText: {
    fontSize: 11,
    fontWeight: '600',
    lineHeight: 11 * 1.4,
    color: colors.accentDark,
    letterSpacing: 1.1,
  },
  scanPreviewHint: {
    fontSize: 12,
    fontWeight: '400',
    lineHeight: 12 * 1.5,
    color: colors.text.secondary,
    marginLeft: 36,
    marginTop: 4,
  },
  permissionCard: {
    justifyContent: 'center',
    alignItems: 'center',
    padding: spacing['3xl'],
    backgroundColor: colors.bg.secondary,
    borderRadius: radii.card,
  },
  permissionTitle: {
    ...typography.title,
    color: colors.text.primary,
    marginTop: spacing.lg,
    marginBottom: spacing.sm,
  },
  permissionText: {
    ...typography.body,
    textAlign: 'center',
    color: colors.text.secondary,
    marginBottom: spacing.xl,
  },
  permissionButton: {
    backgroundColor: colors.accent,
    paddingHorizontal: spacing['2xl'],
    paddingVertical: spacing.md,
    borderRadius: radii.button,
  },
  permissionButtonText: {
    color: '#FFF',
    ...typography.body,
    fontWeight: '700',
  },
  galleryFallback: {
    marginTop: spacing.base,
    padding: spacing.md,
  },
  galleryFallbackText: {
    color: colors.accent,
    ...typography.caption,
  },
  loadingFullscreen: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: colors.bg.primary,
    zIndex: 100,
    elevation: 100,
  },
});

// Re-export guard for the expo-camera CameraView import so the
// permissions hook stays in the bundle even when the user never reaches
// a permission-granted state.
void CameraView;
